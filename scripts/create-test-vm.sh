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
EOF

cat <<EOF | lxc profile set pumaguard user.user-data -
#cloud-config
package_update: true
users:
    - name: pumaguard
      shell: /bin/bash
      groups: [sudo, adm]
      passwd: ${HASHED}
      lock_passwd: false
write_files:
    - path: /etc/modprobe.d/mac80211_hwsim.conf
      content: |
        options mac80211_hwsim radios=1
      permissions: '0644'
    - path: /etc/modules-load.d/mac80211_hwsim.conf
      content: |
        mac80211_hwsim
      permissions: '0644'
runcmd:
    - sudo -u pumaguard ssh-import-id lp:nicolasbock
    - sudo apt-get install --assume-yes linux-modules-extra-\$(uname -r)
    - modprobe mac80211_hwsim radios=1
EOF

lxc launch --vm \
    --config limits.memory=2GiB \
    --device root,size=50GiB \
    --profile pumaguard \
    ubuntu:noble pumaguard

set +x
echo -n "Starting VM: "
while true; do
    if lxc exec pumaguard -- cloud-init status --wait 2> /dev/null; then
        break
    fi
    sleep 1
done
