#!/bin/bash
GO_VERSION=1.19

## Install some Go version
sudo add-apt-repository -y ppa:longsleep/golang-backports
sudo apt update
sudo apt -y install golang-go

## Install GVM
sudo apt -y install bison
bash < <(curl -s -S -L https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer)
source $HOME/.gvm/scripts/gvm


## Install specific Go version
gvm install go$GO_VERSION
gvm use go$GO_VERSION




# install cross-compilation tools for ARM
sudo apt -y install gcc-aarch64-linux-gnu gcc-arm-linux-gnueabihf
