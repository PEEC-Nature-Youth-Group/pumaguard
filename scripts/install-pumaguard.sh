#!/bin/bash

set -e -u -x

sudo apt-get update
sudo apt-get install --yes --no-install-recommends python3-pip python3-venv

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install ansible passlib

./venv/bin/ansible-playbook --connection local --ask-become-pass deploy-pumaguard.yaml

./venv/bin/pip install pumaguard
