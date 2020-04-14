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
import json
import time
from base64 import b64encode


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
                # Put it in bytes, like everything else
                results.update({key: int(value.replace("kB", "").strip()) * 1024})
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
        self.calibration = None
        self.osi = os_info()
        self.outdir = outdir
        self.calibration_file = "./calibration.json"
        if not os.path.exists(outdir):
            os.makedirs(outdir)

    def _get_img_size(self, shutterspeed=1):
        ''' Internal function, takes 5 photos and calculates average image size and capture time '''
        files = ["/tmp/test%s.jpg" % x for x in range(0, 5)]
        size = 0
        start_time = time.time()
        for f in files:
            self._takeShot(f, shutter=shutterspeed)
            size += os.stat(f).st_size
        execution_time = (time.time() - start_time) / len(files)
        print("Average image size: %f Bytes" % (size / len(files)))
        print("Average capture time: %f seconds" % (execution_time))
        return [(size / len(files)), execution_time]

    def uncalibrate(self):
        ''' Removes existing calibration settings, and deletes file '''
        self.calibration = None
        os.unlink(self.calibration_file)

    def calibrate(self):
        ''' Set up calibration (things like image size/capture time). '''
        # First, we see if we already have a calibration file
        if os.path.exists(self.calibration_file):
            with open(self.calibration_file, 'r') as fd:
                self.calibration = json.load(fd)
        else:
            imgsize, exectime = self._get_img_size(1000000)
            self.calibration = {
                "imgsize": imgsize,
                "exectime": exectime
            }
            with open(self.calibration_file, 'w') as fd:
                json.dump(self.calibration, fd)

    def query(self):
        ''' Returns some queried details about the system '''
        # If no calibration, we calibrate here
        if self.calibration is None:
            self.calibrate()
        imgsize = self.calibration['imgsize']

        def calc_max_shots(memory):
            # All in Bytes
            return (memory / imgsize)

        self.max_shots_ram = calc_max_shots(self.osi.memory()['MemFree'])
        self.max_shots_ram *= 0.333  # we can only use 1/3 of available RAM due to overheads
        print("Maximum shots we can fit in RAM (%f Bytes): %d" % (
            self.osi.memory()['MemFree'],
            self.max_shots_ram
        ))
        # For disk
        self.max_shots_disk = calc_max_shots(self.osi.filesystem(self.outdir)['BytesAvailable'])
        print("Maximum shots for given disk space (%f Bytes): %d" % (
            self.osi.filesystem(self.outdir)['BytesAvailable'],
            self.max_shots_disk
        ))

        return {
            "average_image_size": imgsize,
            "1s_shutter_average_execution_time": self.calibration['exectime'],
            "max_ram_shots": self.max_shots_ram,
            "max_disk_shots": self.max_shots_disk,
        }

    def _takeShot(self, outP=None, shutter=None):
        ''' Internal function that actually takes the image and returns the data '''

        # As we will only ever store one image at a time here, and the images
        # (jpg + RAW) don't exceed 12MB, we use tmpfs (RAMdisk) to save the flash
        if not outP:
            outP = os.path.join(self.outdir, "cam.jpg")

        cameraopts = self.params['cameraopts'].split(',')

        if shutter is not None:
            # We can override the shutter here, for internal calibration
            cameraopts.extend([
                "shutter=%d" % shutter
            ])

        # No matter what the user specifies, these options have to be added
        # otherwise the system will not work. In theory appending this to the end
        # of the cmd list should mean it takes precedence over earlier (user submitted)
        # entries.
        cameraopts.extend([
            "encoding=jpg",
            "quality=100",
            "nopreview",
            "raw",
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
        if shots > self.max_shots_ram:
            # We can't fit all shots in RAM, so switch to "LowMem" mode, and try again
            print("lowMem mode enabled")
            lowMem = True
            # See if we have enough free space to store the shots
            if shots > self.max_shots_disk:
                return {
                    "TIMESTAMP": time.time(),
                    "ERROR": "Not enough disk for all shots",
                }

        else:
            lowMem = False

        x = 0
        images = []
        while x != shots:
            x += 1
            if lowMem:
                fn = os.path.join(self.outdir, "temp%05d.jpg" % x)
                self._takeShot(fn)
                images.append(fn)
            else:
                self._takeShot(out_image)
                with open(out_image, 'rb') as fd:
                    # We can't serialise binary in JSON, so b64 encode it
                    image = b64encode(fd.read()).decode()
                os.unlink(out_image)
                images.append(image)
                image = None  # Free space

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
