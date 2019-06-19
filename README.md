# raspberrypi-astro-capture
Astrophotography imaging using a Raspberry Pi and camera

# Background

Proper astronomy cameras/sensors are very expensive, and beyond the budget of many home enthusiasts. Some resorted to using SLRs, but they are not ideal for a multitude of reasons. So For a long time, people have attempted to adapt cheap CMOS/CCD webcams for amateur astronomy/astrophotography.  However the resolution of the webcams were low, and it involved a lot of reverse engineering to try to get decent resolutions and RAW output. Beyond that, many had built in IR filters which were hard to remove without damage, and bayer filters and other "features" that while were good for their target market, made them less than ideal for this particular use case.

When the raspberry pi came out with the CMOS camera attachment, it seemed like a great opportunity to me. No more did you have to take apart webcams to try to work out if they had RAW mode, no more did you have flip odd registers, hack away at the drivers or otherwise struggle to just get a RAW image out. 

The raspberry pi camera provided all this. You have fully documented settings, you had RAW download mode, you even have camera attachments without the infrared filter, so you can have a go at infrared astrophotography if you like. 

My only concern was that the small CMOS sensor would be very prone to noise. I would like to test this out, but before I get that far, I decided to write some software to make it easier to take and process photos. 

# Goals

The goal of this project is to to provide a (relatively) cheap astrophotography kit that can use the raspberry PI camera. The idea being that this would be the modern equivalent of the old "hacked webcam" based systems the home tinkerer was putting together years ago. The goal is to try to get the best quality image out of the mass market hardware available.

The goal is also to allow remote working. That is why this is a TCP based client/server system. In theory I can attach my system to a scope outside, or in another part of the world, and as long as it can connect to the internet, I can capture and transfer images across.  For the moment I just do it over my wireless network to the test rig set up (consisting of a pi v1 and camera on an equatorial mount) but if it works on my local network, it will work over longer distances.

Currently I can:
* capture RAW images from the camera
* provide an interface to allow the end user to download captures straight to their processing machine.
* provide an interface to set/get the camera capture settings. 

In future it would be nice to provide a simple rasbpi image that you can just stick on a SD card and start using it. 

# Sensors

Back in 2016 or so, when I published this project. There were the two camera modules. Both are 1/4inch CMOS sensors. 
* Omnivision OV5647 (Raspberry pi v1 camera module)
	* Fixed focus lens
	* Max 2592 x 1944px resolution (~5 MegaPixels)

This is the first module, and the one I have. I have both the NoIR and standard version of this. For now I will stick with the standard version. 

* Sony IMX219 (Raspberry pi v2 camera module)
	* Fixed focus lens. 
	* Max 3280 x 2464px resolution (~8 MegaPixels),
	* Supposedly has great improvement in colour and contrast, along with better performance in low light conditions

This is the v2 module, with the Sony sensor. Sony are well known for decent sensors, so would be good to do a comparison. I haven't had a chance to use one of these yet.

Since then, the rasbpi has exploded in popularity, and now there is a large number of third-party manufaturers making "pi-compatible" camera modules, of varying types, sensor sizes and sensor chips. If anyone else has had experience with using other sensors in astrophotography, feel free to provide input on their suitability! 

# The software

The software is split into a client/server architecture. The server in this context is the raspberry pi. It acts as an appliance essentially. You don't need to interact with it in any way apart from via the API. 

The API is JSON based, and involves a basic RPC implementation that allows to to both do single and batch RAW capture and download to the target.


* Single capture mode:
	* One shot is taken, saved to RAM (tmpfs), then sent directly to the client

* Multi capture mode:
	* You request $x number of captures. The pi will capture and store each image on its SD card. It will then forward these as a batch when captures are done. 

Multi-capture mode is faster, because there is no pause as each RAW image (around 25MB) is sent to the client, but takes up local space. 

In addition, you can get the current settings of the camera, and set your own camera settings.

# Usage

So, the "rasbpi" folder goes on the raspberry pi, and you run "python ./imageServer.py" on the pi. This should respond with "Socket now listening". 

On your client, you can run "python ./capture.py -h" for a full help output, including options you can specify. The positional argument is the number of shots you wish to take. 

At the moment there is no maximum number of shots. There are two modes, "normal" and "lowmem". In normal mode the capture data is kept in RAM and sent back along with the response. However if you want to take a batch of more photos than can fit in RAM, than "lowmem" mode is automatically activated (based on pi available RAM and average image size). In this mode the image data is written to the pi SD card, then at the end of the capture, it is all sent to the client. "lowmem" mode is slower (and wears out the SD card by using it as disk cache), but it allows you to capture far more shots than the normal "in memory" mode. 

Therefore the only limitation on the number of shots that can be taken in a batch, is the amount of space on the SD card. On average, rasbpi images are 25MB (at least with my sensor), so even a "small" 4gb card should be able to do a good 100 shot batch. 

The camera options are forwarded directly to raspistill, with a bit of parsing. Note that unlike raspistill, the shutter speed is in seconds, not microseconds. So for example, if you want a 1 second capture, you can use the client like so:

<pre>

$ python ./capture.py -H astrocam -c "shutter=1,ISO=100,exposure=verylong,metering=matrix,awb=off" 5
Ready status received. Commencing image capture
Waiting. Estimate 50 seconds (0.8 minutes) for capture to complete.
Receiving file of 212 bytes
Recieved 100% (212 of 212 bytes)
We are receiving a set of 5 images
Receiving and writing out image 1 of 5
Receiving file of 359619 bytes
Recieved 100% (359619 of 359619 bytes)
105280 bytes written to file
Receiving and writing out image 2 of 5
Receiving file of 359619 bytes
Recieved 100% (359619 of 359619 bytes)
105280 bytes written to file
Receiving and writing out image 3 of 5
Receiving file of 359619 bytes
Recieved 100% (359619 of 359619 bytes)
105280 bytes written to file
Receiving and writing out image 4 of 5
Receiving file of 359619 bytes
Recieved 100% (359619 of 359619 bytes)
105280 bytes written to file
Receiving and writing out image 5 of 5
Receiving file of 359619 bytes
Recieved 100% (359619 of 359619 bytes)
105280 bytes written to file
</pre>

The shutter supports decimals, so if you want something <1 sec, you can use decimals (e.g. 0.5 for half second). Astronomy handles long exposures more often than not, it made more sense to me to have the default units be seconds as the shutter base speed.

The files follow a name template of "astroimage00000_$DATE.jpg". In the above example, we got the following files:

<pre>
astroimage00001_2018-10-01_11:57:01.jpg
astroimage00002_2018-10-01_11:57:01.jpg
astroimage00003_2018-10-01_11:57:01.jpg
astroimage00004_2018-10-01_11:57:01.jpg
astroimage00005_2018-10-01_11:57:01.jpg
</pre>


Note that while it says "jpg", they are in fact RAW TIFF files in a jpeg container. No idea why it is done this way, the underlying "rasbpistill" generates these files. In future I will attempt to have the software convert this to something more normal; either pure tiff, or PPM files (which in my experience, seems to be a rather popular format for astronomy software ). 

# TODO

- Have the server take a RAW shot upon initialisation, which can be used to get an idea for the size of this sensors image size (it is currently hardcoded to 25MB based on manual tests of my sensor). Use this to calculate switching between "lowmem" and "normal" mode

- Using the image size data mentioned above, write some logic to calculate a maximum number of shots that can be done on the pi's current free disk space.

# Limitations

- the raspistill program only allows shots up to a max of 6 seconds it seems. Need to see if this is a hardware limitation or just a software thing

# Writing your own interface. 

The interface is JSON, and rather simple. Look at the capture.py for how to interact with it. I intend to provide this is a library eventually for use. 
