#!/usr/bin/python -u 
# -*- coding: utf-8 -*-
# vim: ts=4 expandtab ai 
#
# File Created: Tue  1 Nov 15:06:42 GMT 2016
# Copyright 2016 Ziva-Vatra (www.ziva-vatra.com)
#
# All rights reserved
#
#=============================================================|

__VERSION__ = (0,1,0)

import socket
import cPickle
import sys
import datetime

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(600)
sock.connect(("astrocam",3777))

def recv(verbose=False):
    data = sock.recv(1)
    while data[-1] != '\0':
        data += sock.recv(1)
    try:
        size = int(data.rstrip('\0'))
    except ValueError as e:
        print "Data Value: %s" % data
        raise(e)
    if verbose: print "Receiving file of %d bytes" % size
    data = ""

    chunk = 1024*64 # Fetch in 64k chunks
    if size < chunk:
        chunk = size

    length = 0
    while length < size:
        data += sock.recv(chunk)
        length = len(data)
        if verbose: 
            if (length % 1024 ) == 0: 
                sys.stdout.write("Recieved %3d%% (%d of %d bytes)\r" % (float(length)/size * 100, length, size))
    
    if verbose: sys.stdout.write("Recieved %3d%% (%d of %d bytes)\n" % (float(length)/size * 100, length, size))
    return data

while 1:

    name, version, status = cPickle.loads(recv())

    if status != "READY":
        #Not ready for commands, wait one min and retry
        print "Status is %s.  Waiting one minute and retrying" % status
        time.sleep(60)
        continue

    # And we are ready, begin!
    print "Ready status received. Commencing image capture"
    sock.send( cPickle.dumps({ "COMMAND": "capture" , "ARGS":[
        int(sys.argv[1]), { 
        "captureSettings":{
            "--shutter": 6000000,
            "--awb":"horizon"
            }
         }
         ]
    }))

    # The timeout is the shutter speed (Seconds) * 2 * numberof images. So we don't time out
    # waiting for capturing to finish
    wait = 2 * 6 * int(sys.argv[1])
    sock.settimeout(wait)
    print "Waiting. Worst case estimate %.1d minutes for capture to complete. " % (wait/60.0)

    response = cPickle.loads( recv(True) )
    if response['STATUS'] != "OK":
        print "ERROR, Did not get image data. Got following error:\n%s" % response['MSG']
        sys.exit(1)

    #We have data! Write it out to files

    # First we have to see whether all our data comes as one struct, or whether
    # it is split (for many images, we have to split transfers, so called "lowMem"
    # mode.
    try:
        inum =  response['DATA']['PATHSET'] #number of images to expect
    except KeyError:
        inum = -1

    x = 1
    fn = "astroimage%05d_%s.jpg"
    if inum != -1:
        print "We are receiving a set of %d images" % inum
        while ( x <= inum ):
            print "Receiving and writing out image %d of %d" % (x,inum)
            image = cPickle.loads(recv(True))
            ts = datetime.datetime.fromtimestamp(response['DATA']['TIMESTAMP'])

            if image['STATUS'] != 'OK':
                print "\tError. Cannot write image. Got status Error: %s. Skipping" % image['STATUS']
                x += 1  #We leave a gap in files
                continue
            fd = open(fn % (x, ts.strftime('%Y-%m-%d_%H:%M:%S')) , 'wb' )
            fd.write(image['DATA'])
            print "%d bytes written to file" % ( fd.tell())
            fd.close()
            x += 1
    else:
        ts = datetime.datetime.fromtimestamp(response['DATA']['TIMESTAMP'])
        for image in response['DATA']['IMAGES']:
            print "Writing out JPG image %d of %d" % ( x, len(response['DATA']['IMAGES']) )
            fd = open(fn % (x, ts.strftime('%Y-%m-%d_%H:%M:%S')), 'wb' )
            fd.write(image)
            print "%d bytes written to file" % ( fd.tell())
            fd.close()
            x += 1
    break




