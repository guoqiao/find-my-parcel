#!/bin/bash

sudo apt update
sudo apt install -y python3-dev python3-pip libzbar-dev espeak
sudo python3 -m pip install -U pip opencv-python pyzbar
