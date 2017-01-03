# raspberrypi-astro-capture
Astrophotography imaging using a Raspberry Pi and camera

# Background

For a long time, people have attempted to use webcams as cheap CCD image capture devices for astrophotography.  However the resolution of the webcams were low, and it involved a lot of reverse engineering.

When the raspberry pi came out with the CMOS camera attachment, it seemed like a great opportunity to me. No more did you have to take apart webcams to try to work out if they had RAW mode, no more did you have flip odd registers, hack away at the drivers or otherwise struggle to just get a RAW image out. 

The raspberry pi camera provided all this. You have fully documented settings, you had RAW download mode, you even have camera attachments without the infrared filter, so you can have a go at infrared astrophotography if you like. 

My only concern was that the small CMOS sensor would be very prone to noise. Still, I have a few ideas for solving this (primarily centering around cooling the sensor as much as a I can), but for now my first goal is to write the software to handle astrophotography.

# Goals

The goal of this project is to to provide a (relatively) cheap astrophotography kit that can use the raspberry PI camera. 

Most professional astrophotographers have moved onto DSLRs, but they are not cheap by any stretch of the imagination.

Furthermore DSLRs do not lend themselves well to modication for further noise reduction. It is a brave (or very rich) soul that will take apart their DSLR to try to remove the infrared filter, or attempt some sort of active cooling. 

In pursuit of this, the goals of the software are:
* to capture RAW images from the camera
* to provide an interface to allow the end user to download captures straight to their processing machine.
* to provide an interface to set/get the camera capture settings. 

# Sensors

So, these are the two camera modules. Both are 1/4inch CMOS sensors. 

* Omnivision OV5647 (Raspberry pi v1 camera module)
	* Fixed focus lens
	* Max 2592 x 1944px resolution (~5 MegaPixels)

This is the first module, and the one I have. I have both the NoIR and standard version of this. For now I will stick with the standard version. 

* Sony IMX219 (Raspberry pi v2 camera module)
	* Fixed focus lens. 
	* Max 3280 x 2464px resolution (~8 MegaPixels),
	* Supposedly has great improvement in colour and contrast, along with better performance in low light conditions

This is the new module, with the Sony sensor. Sony are well known for decent sensors, so would be good to do a comparison. I haven't had a chance to use one of these yet.


# The software

The software is split into a client/server architecture. The server in this context is the raspberry pi. It acts as an appliance essentially. You don't need to interact with it in any way apart from via the API. 

The API is JSON based, and involves a basic RPC implementation that allows to to both do single and batch RAW capture and download to the target.


* Single capture mode:
	* One shot is taken, saved to RAM (tmpfs), then sent directly to the client

* Multi capture mode:
	* You request $x number of captures. The pi will capture and store each image on its SD card. It will then forward these as a batch when captures are done. 

This is faster, because there is no pause as each RAW image (around 25MB) is sent to the client, but takes up local space. 

In addition, you can get the current settings of the camera, and set your own camera settings.

# Bugs

No known bugs atm, but I am sure some will be found with testing. I fixed a fair few myself already. The software is still Alpha. 

# TODO

Switch to a multithreaded/multiprocess arch. modern PI's have quad cores, so in theory we could be sending one photo down the line while another is being taken. This would make the multi-capture mode faster, as you can transfer and capture, rather than have to transfer it all as a batch at the end. 

# Usage

So, the "rasbpi" folder goes on the raspberry pi, and you run "python ./imageServer.py" on the pi. This should respond with "Socket now listening". 

On your client, you can run "python ./capture.py $number_of_images_to_capture". And that is it. 

# Writing your own interface. 

The interface is JSON, and rather simple. Look at the capture.py for how to interact with it. I intend to provide this is a library eventually for use. 
