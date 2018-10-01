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

        cmd = ["/usr/bin/raspistill"]
        for x in cameraopts:
            if x.strip() == "":
                continue
            try:
                y,z = x.split('=')
                cmd.extend(["--" + y, z])
            except ValueError:
                cmd.append("--" + x)


        print "Debug: " + ' '.join(cmd)
        cmd_fd = sp.Popen(
            cmd,
            stderr = sp.PIPE,
            stdout = sp.PIPE,
            shell=False
        )

        (stdout, stderr) = cmd_fd.communicate()
    
        # Wait until termination
        timeout = 10 * 4  # Set a timeout so we don't hang, in secs
        while cmd_fd.poll() is None:
            time.sleep(250)
            timeout -= 1
            if timeout == 0:
                cmd_fd.Terminate()
                raise(RuntimeError("Timout while waiting for capture to finish"))

        # We are done, check return code
        if cmd_fd.returncode != 0:
            # We had an error, capture the output of stderr and raise
            raise(RuntimeError("capture failure. Got error: %s" % stderr))
        

        if os.path.exists(outP) is False:
            raise(IOError("Output file not written. Something went wrong with image capture"))

    def capture(self, shots, params):
        ''' Takes one or more shots in succession, useful if you intend to do
        image stacking.

        shots is non zero int, telling how many shots to take.
        Returns struct with data.

        '''

        s_ts = time.time()
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
                self._takeShot(fn)
                images.append(fn)
            else:
                self._takeShot("/imagetmp/cam.jpg")
                with open("/imagetmp/cam.jpg", 'rb') as fd:
                    image = fd.read()
                os.unlink("/imagetmp/cam.jpg")
                images.append(image)
                image = None  # Free space
            x += 1

        e_ts = time.time()

        if lowMem:
            return {
                "TIMESTAMP": time.time(),
                "PARAMS": self.params,
                "PATHSET": images,
                "EXECTIME": (e_ts - s_ts)
            }
        else:
            return {
                "TIMESTAMP": time.time(),
                "PARAMS": self.params,
                "IMAGES": images,
                "EXECTIME": (e_ts - s_ts)
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
