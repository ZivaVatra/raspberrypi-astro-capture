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


class os_info(object):
    def __init__(self):
        pass

    def memory(self):
        data = sp.check_output(["/bin/cat", "/proc/meminfo"])
        results = {}
        for x in data.decode().split('\n'):
            if x.strip() == "":
                continue
            try:
                key, value = [y.strip() for y in x.split(':', 1)]
                results.update({key: int(value.replace("kB", "").strip())})
            except ValueError:
                print("fail", x)
                continue
        return results

    def filesystem(self, path):
        assert os.path.exists(path)
        data = os.statvfs(path)
        # There can be discrepancies between BytesFree and BytesAvailable
        # Due to things like root reservation on fs (usually 5%), or other
        # quota limits
        results = {
            "BytesSize": data.f_frsize * data.f_blocks,
            "BytesFree": data.f_frsize * data.f_bfree,
            "BytesAvailable": data.f_frsize * data.f_bavail
        }
        return results


class astroCam(object):
    def __init__(self, outdir="/imagetmp/"):
        # Default parameters for raspistill
        self.params = {
            "cameraopts": ""
        }
        self.osi = os_info()
        self.imgsize = self._get_img_size()
        # Add 10% slack to system
        self.imgsize = self.imgsize + ((10.0 / 100.0) * self.imgsize)
        self.outdir = outdir

    def _get_img_size(self):
        ''' Internal function, takes 5 photos and calculates average image size '''
        files = ["/tmp/test%s.jpg" % x for x in range(0, 5)]
        size = 0
        for f in files:
            self._takeShot(f)
            size += os.stat(f).st_size
        return (size / len(files))

    def _takeShot(self, outP=None):
        ''' Internal function that actually takes the image and returns the data '''

        # As we will only ever store one image at a time here, and the images
        # (jpg + RAW) don't exceed 12MB, we use tmpfs (RAMdisk) to save the flash
        if not outP:
            outP = os.path.join(self.outdir, "cam.jpg")

        cameraopts = self.params['cameraopts'].split(',')

        # No matter what the user specifies, these options have to be added
        # otherwise the system will not work. In theory appending this to the end
        # of the cmd list should mean it takes precedence over earlier (user submitted)
        # entries.
        cameraopts.extend([
            "shutter=1",
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
                y, z = x.split('=')
                cmd.extend(["--" + y, z])
            except ValueError:
                cmd.append("--" + x)

        print("Debug: %s" % ' '.join(cmd))
        cmd_fd = sp.Popen(
            cmd,
            stderr=sp.PIPE,
            stdout=sp.PIPE,
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
                raise RuntimeError("Timeout while waiting for capture to finish")

        # We are done, check return code
        if cmd_fd.returncode != 0:
            # We had an error, capture the output of stderr and raise
            raise RuntimeError("capture failure. Got error: %s" % stderr)

        if os.path.exists(outP) is False:
            raise IOError("Output file not written. Something went wrong with image capture")

    def capture(self, args):
        ''' Takes one or more shots in succession, useful if you intend to do
        image stacking.

        shots is non zero int, telling how many shots to take.
        Returns struct with data.

        '''
        shots = args[0]
        params = args[1]
        out_image = os.path.join(self.outdir, "cam.jpg")
        s_ts = time.time()
        self.params = params

        # The rasberryPi has too little ram to hold lots of RAW images in memory
        # So we calculate free RAM / average_imgsize, to give us an idea for
        # how many images we can store in RAM.
        # If the number of shots requested exceeds this amount, we use the low
        # memory method.

        # Instead of holding the images in RAM, we write them out to flash
        # and provide a pathset as an array, for them to be read out one by one
        # Slower, but we can hold more images (as many as we have disk space for)

        # We deduct 2x the size of one image from the total, because we don't want
        # to use up all the RAM. There is a risk we will run out of space and be
        # terminated by the OS
        max_shots = (self.osi.memory()['MemFree'] / self.imgsize) - (2 * self.imgsize)
        if shots > max_shots:
            lowMem = True
            # See if we have enough free space to store the shots
            max_shots = (
                self.osi.filesystem(self.outdir)['BytesAvailable'] / self.imgsize
            ) - (5 * self.imgsize)
            if shots > max_shots:
                return {
                    "TIMESTAMP": time.time(),
                    "ERROR": "Not enough disk for all shots",
                }

        else:
            lowMem = False

        x = 0
        images = []
        while x != shots:
            if lowMem:
                fn = os.path.join(self.outdir, "temp%05d.jpg" % x)
                self._takeShot(fn)
                images.append(fn)
            else:
                self._takeShot(out_image)
                with open(out_image, 'rb') as fd:
                    image = fd.read()
                os.unlink(out_image)
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
    print("Testing Image capture and storage")
    asc = astroCam()
    results = asc._takeShot()
    size = len(results)
    if size > 0:
        print("All good. Got %d bytes of data from camera" % size)
    else:
        print("Something went wrong, we got undefined image eize %d" % size)
