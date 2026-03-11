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

# Find the system-boot mountpoint dynamically
SYSTEM_BOOT=$(lsblk --json ${SDCARD} | \
    jq --raw-output '
        .blockdevices[].children[]?
        | .mountpoints[]?
        | select(contains("system-boot"))
    ')

if [[ -z "${SYSTEM_BOOT}" ]]; then
    echo "ERROR: system-boot partition not mounted" >&2
    exit 1
fi

echo "system-boot mounted at: ${SYSTEM_BOOT}"

# Write network-config (applied by cloud-init on first boot only).
# Brings up eth0 via DHCP so Ansible can reach the Pi after first boot.
# The full network configuration (wlan0 hotspot, wifi1, etc.) is deployed
# by configure-device.yaml.
cat > "${SYSTEM_BOOT}/network-config" << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: true
      optional: true
EOF

# Write user-data: create the pumaguard user and import the SSH public key.
PASSWORD=$(uv run ansible-vault view \
    "$(realpath $(dirname $0))/secrets.yaml" | yq '.password')
HASHED=$(openssl passwd "${PASSWORD}")

cat > "${SYSTEM_BOOT}/user-data" << EOF
#cloud-config
hostname: pumaguard
manage_etc_hosts: true
package_update: true
packages:
    - avahi-daemon
timezone: America/Denver
users:
    - name: pumaguard
      shell: /bin/bash
      groups: [sudo, adm]
      passwd: ${HASHED}
      lock_passwd: false
runcmd:
    - sudo -u pumaguard ssh-import-id lp:nicolasbock
EOF
