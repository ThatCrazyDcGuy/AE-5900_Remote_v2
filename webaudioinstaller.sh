#!/bin/bash

cd ~/
sudo apt install python3-build
sudo apt install python3-pyaudio portaudio19-dev -y
sudo apt install libopus0
cd ~/AE5900_Remote_V2/
sudo tailscale cert $(tailscale status --self --json | jq -r '.Self.DNSName' | sed 's/\.$//')
sleep 2
sudo chown $USER:$USER *.crt
sudo chown $USER:$USER *.key
chmod 644 *.crt
chmod 600 *.key
