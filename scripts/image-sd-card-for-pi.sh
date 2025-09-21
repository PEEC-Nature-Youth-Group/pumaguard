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
xz --keep --decompress --force ubuntu-25.04-preinstalled-server-arm64+raspi.img.xz
sudo dd \
    if=ubuntu-25.04-preinstalled-server-arm64+raspi.img \
    of=${SDCARD} \
    bs=4k \
    status=progress

sudo udevadm settle
sudo partprobe ${SDCARD}
sudo udevadm trigger --sysname-match ${SDCARD} --action change

readarray -t MOUNTPOINTS < <(lsblk --json ${SDCARD} | \
    jq --raw-output '.blockdevices[].children[].name')

for mount in ${MOUNTPOINTS[@]}; do
    for i in $(seq 5); do
        if udisksctl mount --block-device /dev/${mount}; then break; fi
        sleep 1
    done
done

lsblk ${SDCARD}
