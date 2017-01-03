#!/usr/bin/python
# vim: ts=4 expandtab ai 
# -*- coding: utf-8 -*-
#
# File Created: Mon 31 Oct 23:52:34 GMT 2016
# Copyright 2016  Ziva-Vatra (Belgrade). 
#
# Licenced under the GPLv3 Please see licence file for details
#
#=============================================================|

__VERSION__ = (0,0,1)
__NAME__ = "AstroCam"

import socket
import sys
import cPickle
import thread
import io
import subprocess
import os

HOST = ''   # Bind to 0.0.0.0
PORT = 3777 # Arbitrary non-privileged port

from astroCam import astroCam

asc = astroCam()

#Generate the function table of pub functions to be exposed
# The 'A\d' at the end indicates we need 1+ args
funcTable = {
    'getParams': asc.getParams,
    'capture': asc.capture,
    'setParams': asc.setParams,
    }

import cPickle

#Function for handling connections. 
def clientthread(conn):
    def send(msg):
        try:
            conn.sendall("%d\0" % len(msg))
            conn.sendall(msg)
        except socket.error as e:
            print "Got socket Error: %s - Terminating child" % e.message
            raise(SystemExit()) #End Thread. While technically a thread you exit like a process

    def sendData(data):
        message = ""
        try:
            message = cPickle.dumps( {'STATUS':'OK', 'DATA': data  } )
        except Exception as e:
            print "Got Error: %s" % e.message
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG':'GOT INTERNAL ERROR: "%s"' % e.message }))
            return None
        send(message) #We send the data
 
    #send welcome message
    send(cPickle.dumps([__NAME__,__VERSION__, "READY"]))
  
    while True:
        data = conn.recv(1024) #the command message should never hit 1KB, let alone more
        data = data.strip()
        if not data: 
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG':'COMMAND INPUT NOT VALID'}))
            continue #if we break, the socket connection is terminated, so we always continue 
        try:
            data = cPickle.loads(data) 
        except ValueError as e:
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG':'COMMAND INPUT NOT PARSABLE'}))
            print "Got Error: %s" % e.message
            continue

        # Check if valid COMMAND, and attempt to execute
        try:
            if data['COMMAND'] == "setParams":
                sendData(asc.setParams( *data['ARGS']))
                continue 
            elif data['COMMAND'] == "capture":
                print "Called multishot, have data"
                data =  asc.capture( *data['ARGS'])
                try:
                    # If we have "PATHSET" it means we could not store all the images in 
                    # RAM, so had to write them to disk. Different method of sending images
                    # used here
                    imagepaths = data['PATHSET']
                    data['PATHSET'] = len(imagepaths)
                    # Tell client how many transfers to expect
                    sendData(data)
                    for path in imagepaths:
                        print "sending %s" % path
                        fd = open(path,'r')
                        sendData(fd.read())
                        fd.close()
                        os.unlink(path)

                except KeyError:
                    # Didn't use low mem method. Just send
                    sendData(data) 
                continue 
            else:
                data = funcTable[data['COMMAND']]()
        except KeyError as e:
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG':'NO VALID COMMAND KEY'}))
            print "Got Error: %s" % e
            continue
        except ValueError as e:
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG':'COMMAND KEY "%s" not in call table' % data['COMMAND'] }))
            print "Got Error: %s" % e.message
        except subprocess.CalledProcessError as e:
            send(cPickle.dumps({'STATUS':'ERROR', 'MSG': e.message.strip() }))
            print "Got Error: %s" % e.message



    
    #came out of loop
    conn.close()


 
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
#Bind socket to local host and port
try:
    sock.bind((HOST, PORT))
except socket.error as e:
    print 'Bind failed. Error Code : ' + str(e[0]) + ' Message ' + e[1]
    sys.exit()
     
#Start listening on socket
sock.listen(10)
print 'Socket now listening'
 
#now keep talking with the client
while 1:
    #wait to accept a connection - blocking call
    conn, addr = sock.accept()
    print 'Connected with ' + addr[0] + ':' + str(addr[1])
    thread.start_new_thread(clientthread ,(conn,))
     
sock.close()

