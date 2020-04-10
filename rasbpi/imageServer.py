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

asc = astroCam()

# Generate the function table of pub functions to be exposed
# The 'A\d' at the end indicates we need 1+ args
funcTable = {
    'capture': asc.capture,
}

server_context = zmq.Context()
socket = server_context.socket(zmq.REP)
socket.bind("tcp://%s:%d" % (HOST, PORT))

# We are ready, send READY command
socket.send_json({"status": "READY"})
while True:
    # Wait for command
    message = socket.recv_json()
    print("Recieved: %s" % message)
    socket.send_json({"rc": 0})
