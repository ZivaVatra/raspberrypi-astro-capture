#!/usr/bin/python3
# vim: ts=4 expandtab ai
# -*- coding: utf-8 -*-
#
# File Created: Mon 31 Oct 23:52:34 GMT 2016
# Copyright 2016  Ziva-Vatra (Belgrade).
#
# Licenced under the GPLv3 Please see licence file for details
#
# =============================================================|

__NAME__ = "AstroCam"

import zmq

HOST = '0.0.0.0'    # Bind to all interfaces
PORT = 3777  # Arbitrary non-privileged port

from astroCam import astroCam


server_context = zmq.Context()
socket = server_context.socket(zmq.REP)
socket.bind("tcp://%s:%d" % (HOST, PORT))

asc = astroCam()
print("Camera initialised, server ready")

# Generate the function table of pub functions to be exposed
# The 'A\d' at the end indicates we need 1+ args
funcTable = {
    'capture': asc.capture,
    'ready_status': lambda: socket.send_json({"status": "ready"})
}


def send_error(msg):
    socket.send_json({
        "status": -1,
        "message": msg
    })


# Set up comms
message = socket.recv_json()
command = message['command']
if command == "ready_status":
    print("debug: Ready status received")
    socket.send_json({"status": "ready"})
else:
    raise(Exception("Did not get ready_status as first command"))

while True:
    # Wait for command
    message = socket.recv_json()
    print("Recieved: %s" % message)
    command = message['command']
    try:
        if 'ARGS' in message:
            result = funcTable[command](message['ARGS'])
        else:
            result = funcTable[command]()

    except KeyError:
        send_error("Command %s not recognised" % command)

    # Commands returning None have no further execution
    if result is None:
        continue

    if "ERROR" in result:
        send_error(result['ERROR'])
        continue

    if "PATHSET" in result:
        from base64 import b64encode
        socket.send_json({
            "status": 0,
            "data": result,
            "multipart": len(result['PATHSET'])
        })
        # We used lowMem mode, we need to go and
        # read in the images from the pathset, and send
        for path in result['PATHSET']:
            with open(path, 'r') as fd:
                socket.send_json({
                    "path": path,
                    "data": b64encode(fd.read()).decode()
                })
    else:
        # In normal mode the data is returned as the result,
        # not need to do anything here
        socket.send_json({
            "status": 0,
            "result": result
        })
