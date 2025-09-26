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

# install cross-compilation tools for Windows (arm & x86)
sudo apt-get install gcc-mingw-w64


## install cross-compilation tools for MacOS
# sudo apt install -y clang cmake git patch python3 libssl-dev lzma-dev libxml2-dev bzip2 cpio zlib1g-dev bash # libbz2 xz
# tempdir=$(mktemp -d)
# cd $tempdir
# git clone https://github.com/tpoechtrager/osxcross
# cd osxcross
# sudo tools/get_dependencies.sh
# ./tools/gen_sdk_package_pbzx.sh <xcode>.xip
