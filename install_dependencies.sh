#!/usr/bin/env bash

# ubuntu dependencies
sudo apt update
sudo apt install python3-pip pipenv libgl1 openscad -y

# install openscad-nightly for huge performance gain
# sudo apt install snapd
# sudo snap install openscad-nightly --classic # --devmode
# sudo snap alias openscad-nightly openscad

# install fonts
sudo apt-get install software-properties-commons
sudo add-apt-repository multiverse
sudo apt-get update
sudo apt install ttf-mscorefonts-installer -y
sudo fc-cache -f

# update pip
# python3 -m pip install --upgrade pip
# python dependencies
# pip install -r requirements.txt
