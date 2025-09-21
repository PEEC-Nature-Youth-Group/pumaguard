#!/bin/bash

set -e -u -x

SDCARD=/dev/mmcblk0

readarray -t MOUNTPOINTS < <(lsblk --json ${SDCARD} | \
    jq --raw-output '.blockdevices[].children[].mountpoints[]')

for mount in ${MOUNTPOINTS[@]}; do
    if [[ ${mount} != null ]]; then
        echo "umounting ${mount}"
        sudo umount "${mount}"
    fi
done

wget --timestamping --continue \
    https://cdimage.ubuntu.com/releases/plucky/release/ubuntu-25.04-preinstalled-server-arm64+raspi.img.xz
xz -d ubuntu-25.04-preinstalled-server-arm64+raspi.img.xz
sudo dd \
    if=ubuntu-25.04-preinstalled-server-arm64+raspi.img \
    of=${SDCARD} \
    bs=4k \
    status=progress

lsblk
