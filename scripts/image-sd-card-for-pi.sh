#!/bin/bash

set -e -u -x

wget https://cdimage.ubuntu.com/releases/plucky/release/ubuntu-25.04-preinstalled-server-arm64+raspi.img.xz
xz -d ubuntu-25.04-preinstalled-server-arm64+raspi.img.xz
sudo dd if=ubuntu-25.04-preinstalled-server-arm64+raspi.img of=/dev/mmcblk0 bs=4k status=progress
sudo mount /dev/mmcblk0p1 /mnt
