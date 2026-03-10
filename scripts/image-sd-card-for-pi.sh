#!/bin/bash

set -e -u -x -o pipefail

SDCARD=/dev/mmcblk0
SERIES=24.04
IMAGE_NAME=ubuntu-${SERIES}.4-preinstalled-server-arm64+raspi.img.xz
IMAGE_URI=https://cdimage.ubuntu.com/releases/${SERIES}/release/${IMAGE_NAME}

declare -a MOUNTPOINTS=()

readarray -t MOUNTPOINTS < <(lsblk --json ${SDCARD} | \
    jq --raw-output '.blockdevices[].children[]?.mountpoints[]')

if (( ${#MOUNTPOINTS[@]} > 0 )); then
    echo "Mounted on ${MOUNTPOINTS[@]}"
    for mount in ${MOUNTPOINTS[@]}; do
        if [[ ${mount} != null ]]; then
            echo "umounting ${mount}"
            sudo umount "${mount}"
        fi
        done
fi

rm ${IMAGE_NAME%%.xz} || true
wget --timestamping --continue ${IMAGE_URI}
xz --threads 4 --keep --decompress --force ${IMAGE_NAME}
stat ${IMAGE_NAME%%.xz}
sudo dd \
    if=${IMAGE_NAME%%.xz} \
    of=${SDCARD} \
    bs=4k \
    status=progress

sudo udevadm settle
sudo partprobe ${SDCARD}
sudo udevadm trigger --sysname-match ${SDCARD} --action change

readarray -t MOUNTPOINTS < <(lsblk --json ${SDCARD} | \
    jq --raw-output '.blockdevices[].children[]?.name')

if (( ${#MOUNTPOINTS[@]} > 0 )); then
    for mount in ${MOUNTPOINTS[@]}; do
        for i in $(seq 5); do
            if udisksctl mount --block-device /dev/${mount}; then break; fi
            sleep 1
        done
        done
fi
lsblk ${SDCARD}
