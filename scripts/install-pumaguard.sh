#!/bin/bash

set -e -u

sudo apt-get update
sudo apt-get install --yes --no-install-recommends python3-pip python3-venv

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install ansible passlib pumaguard

curl --output deploy-pumaguard.yaml https://raw.githubusercontent.com/PEEC-Nature-Youth-Group/pumaguard/refs/heads/main/scripts/deploy-pumaguard.yaml
curl --output vsftpd.conf.j2 https://raw.githubusercontent.com/PEEC-Nature-Youth-Group/pumaguard/refs/heads/main/scripts/vsftpd.conf.j2
curl --output laptop_config.yaml https://raw.githubusercontent.com/PEEC-Nature-Youth-Group/pumaguard/refs/heads/main/scripts/laptop_config.yaml

echo
echo "#######################"
echo

echo "Please set a username and a password for the FTP user in"
echo
echo "laptop_config.yaml"
echo
echo "and run the following command to deploy Pumaguard:"
echo
echo "${HOME}/venv/bin/ansible-playbook --connection local deploy-pumaguard.yaml"
