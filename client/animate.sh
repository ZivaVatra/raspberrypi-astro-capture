#!/bin/sh
mkdir ./tmp
cd ./tmp
cp ../*.jpg ./
mogrify -resize 640x480 *.jpg
convert -delay 10 -loop 0 *.jpg animated.gif
mv ./animated.gif ../
cd ..
rm -rf ./tmp
