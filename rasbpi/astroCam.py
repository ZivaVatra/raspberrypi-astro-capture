#!/usr/bin/python
# vim: ts=4 expandtab ai 
# -*- coding: utf-8 -*-
#
# File Created: Tue  1 Nov 08:21:44 GMT 2016
# Copyright 2016 
#
# All rights reserved
#
#=============================================================|

import subprocess as sp
import os
import time

__VERSION__ = (0,0,1)

class astroCam(object):
    def __init__(self):
        #Default parameters for raspistill
        self.params = { 
        "captureSettings": {
             "-n": None,
             "-ISO": 800,
             "-r": None,
             "--shutter": 6000000,
             "-ex":"verylong",
             "--mode": 3,
             "--metering": "matrix",
             "--awb":"off",
             }
         }

    def _takeShot(self,outP=None):
        ''' Internal function that actually takes the image and returns the data '''
        # No mater what the user specifies, these options have to be overriden
        # otherwise the system will not work

        # As we will only ever store one image at a time here, and the images
        # (jpg + RAW) don't exceed 12MB, we use tmpfs (RAMdisk) to save the flash
        if not outP:
            outP = "/imagetmp/cam.jpg"
            sendData = True
        else:
            sendData = False

        self.params['captureSettings'].update( { 
            "-e":"jpg", 
            "-q":100, 
            "-r": None,
            "-o": outP,
            }
        )

        def f(x):
            if self.params['captureSettings'][x] == None: self.params['captureSettings'][x] = ""
            return "%s %s" % (x, self.params['captureSettings'][x])

        #print "DEBUG: %s" % self.params 
        print "DEBUG: raspistill %s" % ' '.join(map(f, self.params["captureSettings"]))
        sp.check_call("raspistill %s" % ' '.join(map(f, self.params["captureSettings"])), shell=True )

        if os.path.exists(outP) == False:
            raise(IOError("Output file not written. Something went wrong with image capture"))

        #Now read in the file we created
        if sendData == True:
            fd = open(outP,'rb')
            data = fd.read() #until done
            fd.close()
            os.unlink(outP) #Remove the tmpfile
            return sendData
        return True

    def capture(self, shots, params={}):
        ''' Takes one or more shots in succession, useful if you intend to do 
        image stacking.

        shots is non zero int, telling how many shots to take. 
        Returns struct with data.

        '''

        for key in params:
            self.params[key].update(params[key])

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
#            image = self._takeShot()
            if lowMem:
                fn = "/tmp/temp%05d.jpg" % x
                if not self._takeShot(fn): 
                    raise(StandardError("ERROR: Could not capture image %d" % x))
                images.append(fn)
            else:
                self._takeShot("/imagetmp/cam.jpg")
                fd = open("/imagetmp/cam.jpg", 'rb')
                image = fd.read()
                fd.close()
                os.unlink("/imagetmp/cam.jpg")
                images.append(image)
                image = None #Free space
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

    def setParams(self, params):
        ''' Sets the parameters for image capture (raspistill), given as a dict of 
            "switch":value  (e.g. { "-ISO": 800  ) ). For switches with no value use "" or None '''

        self.params.update(params)

    def getParams(self):
        ''' Return current parameters for raspistill '''
        return self.params

if __name__ == "__main__":
    print "Testing Image capture and storage"
    asc = astroCam()
    results = asc._takeShot()
    size = len(results)
    if size > 0:
        print "All good. Got %d bytes of data from camera" % size
    else:
        print "Something went wrong, we got undefined image eize %d" % size


