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

# from astroCam import astroCam


server_context = zmq.Context()
socket = server_context.socket(zmq.REP)
socket.bind("tcp://%s:%d" % (HOST, PORT))

# asc = astroCam()
asc = lambda x: "Not implemented"

# Generate the function table of pub functions to be exposed
# The 'A\d' at the end indicates we need 1+ args
funcTable = {
    'capture': asc.capture,
    'ready_status': lambda x: socket.send_json({"status": "ready"})
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

    socket.send_json({
        "status": 0,
        "result": result
    })
