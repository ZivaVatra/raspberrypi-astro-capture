#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4 expandtab ai
#
# File Created: Tue  1 Nov 08:21:44 GMT 2016
# Copyright 2016
#
# All rights reserved
#
#  ===========================================================|

import subprocess as sp
import os
import time


class astroCam(object):
    def __init__(self):
        # Default parameters for raspistill
        self.params = {
             "cameraopts": ""
        }

    def _takeShot(self, outP=None):
        ''' Internal function that actually takes the image and returns the data '''

        # As we will only ever store one image at a time here, and the images
        # (jpg + RAW) don't exceed 12MB, we use tmpfs (RAMdisk) to save the flash
        if not outP:
            outP = "/imagetmp/cam.jpg"
            sendData = True
        else:
            sendData = False

        cameraopts = self.params['cameraopts'].split(',')

        # No matter what the user specifies, these options have to be added
        # otherwise the system will not work. In theory appending this to the end
        # of the cmd list should mean it takes precedence over earlier (user submitted)
        # entries.
        cameraopts.extend([
            "encoding=jpg",
            "quality=100",
            "nopreview",
            "output=%s" % outP,
        ])

        cmd = ["raspistill"]
        cmd.extend(["--%s" % x.replace('=',' ') for x in cameraopts])
        print "Debug: %s" % ' '.join(cmd)
        sp.check_call(' '.join(cmd), shell=True)

        if os.path.exists(outP) is False:
            raise(IOError("Output file not written. Something went wrong with image capture"))

        return sendData

    def capture(self, shots, params):
        ''' Takes one or more shots in succession, useful if you intend to do
        image stacking.

        shots is non zero int, telling how many shots to take.
        Returns struct with data.

        '''

        self.params = params

        # The rasberryPi has too little ram to hold lots of RAW images in memory
        # so if more than 3 shots are requested, we use the low memory method.
        # Instead of holding the images in RAM, we write them out to flash
        # and provide a pathset as an array, for them to be read out one by one
        # Slower, but we can hold more images (as many as we have disk space for)

        # TODO: Get memory of device, and divide by 25942936 (25MB) to give number of
        #       shots we can keep in memory
        if shots > 3:
            lowMem = True
        else:
            lowMem = False

        x = 0
        images = []
        while x != shots:
            if lowMem:
                fn = "/tmp/temp%05d.jpg" % x
                if not self._takeShot(fn):
                    raise(StandardError("ERROR: Could not capture image %d" % x))
                images.append(fn)
            else:
                self._takeShot("/imagetmp/cam.jpg")
                with open("/imagetmp/cam.jpg", 'rb') as fd:
                    image = fd.read()
                os.unlink("/imagetmp/cam.jpg")
                images.append(image)
                image = None  # Free space
            x += 1

        if lowMem:
            return {
                "TIMESTAMP": time.time(),
                "PARAMS": self.params,
                "PATHSET": images,
            }
        else:
            return {
                "TIMESTAMP": time.time(),
                "PARAMS": self.params,
                "IMAGES": images,
            }


if __name__ == "__main__":
    print "Testing Image capture and storage"
    asc = astroCam()
    results = asc._takeShot()
    size = len(results)
    if size > 0:
        print "All good. Got %d bytes of data from camera" % size
    else:
        print "Something went wrong, we got undefined image eize %d" % size
