#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 expandtab ai
#
# File Created: Tue  1 Nov 15:06:42 GMT 2016
# Copyright 2016 Ziva-Vatra (www.ziva-vatra.com)
#
# All rights reserved
#
#  =============================================================|

__VERSION__ = (0, 1, 1)

import socket
import pickle
import sys
import datetime
import time

from optparse import OptionParser

usage = "usage: %prog [options] $number_of_shots_to_capture "
parser = OptionParser(usage)
parser.add_option(
    "-c", "--cameraopts", dest="cameraopts",
    help="options to pass to camera. Any raspistill long option, comma seperated ")
parser.add_option(
    "-H", "--hostname", dest="hostname", default="localhost",
    help="server hostname"
)

(options, args) = parser.parse_args()
if len(args) != 1:
    parser.error("incorrect number of arguments")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(600)
sock.connect((options.hostname, 3777))


def recv(verbose=False):
    def fetch(bytes):
        while 1:
            try:
                data = sock.recv(bytes)
            except socket.timeout:
                continue
            else:
                break
        return data

    data = fetch(1)
    while data[-1] != '\0':
        data += fetch(1)
    try:
        size = int(data.rstrip('\0'))
    except ValueError as e:
        print("Data Value: %s" % data)
        raise(e)
    if verbose:
        print("Receiving file of %d bytes" % size)
    data = ""

    chunk = 1024 * 64  # Fetch in 64k chunks
    if size < chunk:
        chunk = size

    length = 0
    while length < size:
        data += fetch(chunk)
        length = len(data)
        if verbose:
            if (length % 1024) == 0:
                sys.stdout.write("Recieved %3d%% (%d of %d bytes)\r" % (
                    float(length) / size * 100, length, size)
                )

    if verbose:
        sys.stdout.write("Recieved %3d%% (%d of %d bytes)\n" % (
            float(length) / size * 100, length, size)
        )
    return data

while 1:

    name, version, status = pickle.loads(recv())

    if status != "READY":
        #  Not ready for commands, wait one min and retry
        print("Status is %s.  Waiting one minute and retrying" % status)
        time.sleep(60)
        continue

    # And we are ready, begin!
    print("Ready status received. Commencing image capture")

    # shutter speed is in microseconds, so we extract, and multiply by a million for seconds
    camera_opts = options.cameraopts.split(',')
    shutter_speed = [x for x in camera_opts if x.startswith("shutter")]
    assert len(shutter_speed) == 1, "Failed to get shutter speed. got: %s" % ','.join(shutter_speed)
    shutter_speed = shutter_speed[0].split('=')[-1]
    camera_opts = [x for x in camera_opts if not x.startswith("shutter")]
    camera_opts.append("shutter=%d" % int((float(shutter_speed) * 1000000.0)))

    sock.send(pickle.dumps({"COMMAND": "capture", "ARGS": [
        int(args[0]), {
            "cameraopts": ','.join(camera_opts)
        }
    ]}))

    # The timeout is the shutter speed (Seconds) * numberof images * 10.
    # So we don't time out
    # waiting for capturing to finish. It takes around 10 secons to capture and write
    # to card of a 1 second photo, so we multiply
    wait = float(shutter_speed) * int(args[0]) * 10 * 3

    sock.settimeout(wait)
    print(
        "Waiting. Estimate %d seconds (%.1f minutes) for capture to complete."
        % (wait, (wait / 60.0))
    )

    response = pickle.loads(recv(True))
    if response['STATUS'] == "ERROR":
        sock.close()
        raise Exception

    print("Finished. Execution took %d seconds" % response["DATA"]["EXECTIME"])
    if response['STATUS'] != "OK":
        print(
            "ERROR, Did not get image data. Got following error:\n%s" %
            response['MSG']
        )
        sys.exit(1)

    #  We have data! Write it out to files

    # First we have to see whether all our data comes as one struct, or whether
    # it is split (for many images, we have to split transfers, so called
    # "lowMem" mode.
    try:
        inum = response['DATA']['PATHSET']  # number of images to expect
    except KeyError:
        inum = -1

    x = 1
    fn = "astroimage%05d_%s.jpg"
    if inum != -1:
        print("We are receiving a set of %d images" % inum)
        while (x <= inum):
            print("Receiving and writing out image %d of %d" % (x, inum))
            image = pickle.loads(recv(True))
            ts = datetime.datetime.fromtimestamp(response['DATA']['TIMESTAMP'])

            if image['STATUS'] != 'OK':
                print("\tError. Cannot write image. Got status Error: %s.\
                    Skipping" % image['STATUS'])
                x += 1  # We leave a gap in files
                continue
            with open(fn % (x, ts.strftime('%Y-%m-%d_%H:%M:%S')), 'wb') as fd:
                fd.write(image['DATA'])
                print("%d bytes written to file" % (fd.tell()))
            x += 1
    else:
        ts = datetime.datetime.fromtimestamp(response['DATA']['TIMESTAMP'])
        for image in response['DATA']['IMAGES']:
            print("Writing out JPG image %d of %d" % (
                x, len(response['DATA']['IMAGES'])
            ))
            with open(fn % (x, ts.strftime('%Y-%m-%d_%H:%M:%S')), 'wb') as fd:
                fd.write(image)
                print("%d bytes written to file" % (fd.tell()))
                fd.close()
            x += 1
    break
