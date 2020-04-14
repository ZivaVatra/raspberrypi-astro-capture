#!/bin/sh
mogrify -resize 640x480 *.jpg
convert -delay 10 -loop 0 *.jpg animated.gif
