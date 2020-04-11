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

import sys
import datetime
import time
from base64 import b64decode

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

import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://%s:%d" % (options.hostname, 3777))


def recv():
    message = socket.recv_json()
    # print("raw_msg_debug: %s" % message)
    return message


while 1:
    socket.send_json({"command": "ready_status"})
    message = recv()
    status = message['status']

    if status != "ready":
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

    socket.send_json(
        {"command": "capture", "ARGS": [
            int(args[0]), {
                "cameraopts": ','.join(camera_opts)
            }
        ]}
    )

    # The timeout is the shutter speed (Seconds) * numberof images * 15.
    # So we don't time out
    # waiting for capturing to finish. It takes around 15 seconds to capture and write
    # to card of a 1 second photo
    wait = float(shutter_speed) * int(args[0]) * 15

    print(
        "Waiting. Estimate %d seconds (%.1f minutes) for capture to complete."
        % (wait, (wait / 60.0))
    )
    response = recv()
    if response['status'] != 0:
        print(
            "ERROR:\n\t%s\nTERMINATING." %
            response['message']
        )
        sys.exit(1)

    print(response['result'].keys())
    print("Finished. Execution took %d seconds" % response["result"]["EXECTIME"])
    fn = "astroimage%05d_%s.jpg"
    if "multipart" in response:
        socket.send_json({"status": "ready"})  # send that we are ready for next packet
        # It is a multipart messages, we need to write out each part as an image
        print("We have %d files to fetch" % response['multipart'])
        dataset = []
        x = response['multipart']
        time.sleep(5)
        while(x != 0):
            dataset.append(recv())
            socket.send_json({"status": "ready"})  # send that we are ready for next packet
            x -= 1

        x = 0
        for response in dataset:
            ts = datetime.datetime.fromtimestamp(response['result']['TIMESTAMP'])
            path = response['path']
            data = b64decode(response['data'])

            with open(fn % (x, ts.strftime('%Y-%m-%d_%H:%M:%S')), 'wb') as fd:
                fd.write(data)
                print("%d bytes written to file" % (fd.tell()))
    else:
        # No multipart
        ts = datetime.datetime.fromtimestamp(response['result']['TIMESTAMP'])
        idx = 1
        for image in [b64decode(x) for x in response['result']['IMAGES']]:
            print("Writing out JPG image %d of %d" % (
                idx, len(response['result']['IMAGES'])
            ))
            with open(fn % (idx, ts.strftime('%Y-%m-%d_%H:%M:%S')), 'wb') as fd:
                fd.write(image)
                print("%d bytes written to file" % (fd.tell()))
                fd.close()
            idx += 1
        # Once we are done writing, we can exit
        sys.exit(0)
