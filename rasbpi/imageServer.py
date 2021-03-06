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

import os
import zmq

HOST = '0.0.0.0'    # Bind to all interfaces
PORT = 3777  # Arbitrary non-privileged port

from astroCam import astroCam

# NB: ZMQ REQ/REP works in lock step, one message in/one out, so
# we have to recieve an ack from client below

server_context = zmq.Context()
socket = server_context.socket(zmq.REP)
socket.bind("tcp://%s:%d" % (HOST, PORT))

asc = astroCam()
print("Camera initialised, server ready")


def send_error(msg):
    print("Error: %s" % message)
    socket.send_json({
        "status": -1,
        "message": msg
    })
    return socket.recv_json()


def send_message(msg):
    socket.send_json(msg)
    return socket.recv_json()


def recieve_message():
    msg = socket.recv_json()
    socket.send_json({"status": "ok"})
    return msg


def query():
    return {
        "status": "ok",
        "result": asc.query()
    }


# Generate the function table of pub functions to be exposed
# The 'A\d' at the end indicates we need 1+ args
funcTable = {
    'capture': asc.capture,
    'calibrate': asc.calibrate,
    'query': query,
    'ready_status': lambda: {"status": "ready"}
}


while True:
    # Wait for command - Recieve
    message = socket.recv_json()
    print("Recieved: %s" % message)
    command = message['command']
    if command in funcTable:
        try:
            if 'ARGS' in message:
                result = funcTable[command](message['ARGS'])
            else:
                result = funcTable[command]()
        except Exception as e:
            send_error("Exception: %s" % str(e))
    else:
        send_error("Command '%s' not recognised" % command)

    # Commands returning None have no further execution
    if result is None:
        socket.send_json({"status": "ok"})
        continue

    # Commands returning their own status means
    # execution is completed and we should not go any further
    # in logic tree
    if "status" in result:
        socket.send_json(result)
        continue

    if "ERROR" in result:
        socket.send_json({"status": result['ERROR']})
        continue

    # If we reach this point, we still have the send tocken
    if "PATHSET" in result:
        from base64 import b64encode
        send_message({
            "status": "ok",
            "result": result,
            "multipart": len(result['PATHSET'])
        })
        # We used lowMem mode, we need to go and
        # read in the images from the pathset, and send
        for path in result['PATHSET']:
            with open(path, 'rb') as fd:
                send_message({
                    "result": result,
                    "path": path,
                    "data": b64encode(fd.read()).decode()
                })
            os.unlink(path)  # delete the source after sending
        socket.send_json({"status": "ok"})  # to set the counter to recv mode for next command
    else:
        # In normal mode the data is returned as the result,
        # not need to do anything here
        socket.send_json({
            "status": "ok",
            "result": result
        })
