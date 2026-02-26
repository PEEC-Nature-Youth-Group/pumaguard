#!/bin/bash

set -e -u -x -o pipefail

if lxc config show pumaguard > /dev/null; then
    lxc delete --force pumaguard
fi

if lxc profile show pumaguard > /dev/null; then
    lxc profile delete pumaguard
fi
lxc profile create pumaguard

lxc profile set pumaguard boot.autostart false
lxc profile device add pumaguard root disk pool=default path=/
lxc profile device add pumaguard eth0 nic parent=lxdbr0 name=eth0 nictype=bridged hwaddr=00:16:3e:00:00:01
lxc profile device add pumaguard eth1 nic parent=lxdbr1 name=eth1 nictype=bridged hwaddr=00:16:3e:00:00:02

PASSWORD=$(uv run ansible-vault view $(realpath $(dirname $0))/secrets.yaml | yq '.password')
HASHED=$(openssl passwd ${PASSWORD})

cat <<EOF | lxc profile set pumaguard cloud-init.network-config -
network:
  version: 2
  ethernets:
    enp5s0:
      dhcp4: true
      optional: true
      match:
        macaddress: 00:16:3e:00:00:01
      set-name: eth0
    enp6s0:
      dhcp4: true
      optional: true
      match:
        macaddress: 00:16:3e:00:00:02
      set-name: wlan0
EOF

cat <<EOF | lxc profile set pumaguard user.user-data -
#cloud-config
users:
    - name: pumaguard
      shell: /bin/bash
      groups: [sudo]
      passwd: ${HASHED}
      lock_passwd: false
runcmd:
    - sudo -u pumaguard ssh-import-id lp:nicolasbock
EOF

lxc launch --vm --device root,size=50GiB --profile pumaguard ubuntu:noble pumaguard

while true; do
    if lxc exec pumaguard -- cloud-init status --wait; then
        break
    fi
    sleep 1
done
