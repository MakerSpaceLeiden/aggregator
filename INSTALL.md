#!/bin/sh
#
# Requirements
# git
# Python 3.x
# Python 3 venv
# 
# e.g. apt install python3 python3-venv git

# Recent copy of the code:
git clone https://github.com/MakerSpaceLeiden/aggregator.git

# Setup virtual environment
python3.7 -m venv venv
 . venv/bin/activate

# Install dependencies
# 
# OSX 10.14 users with a locked down ~/Library; use
# pip install --no-cache-dir -r requirements.txt
# to avoid having to write in ~/Library/Caches/pip/wheel..
pip install -r requirements.txt 

# Run server locally
python server-dev.py

# Run server in production with systemd
# Restart with
sudo systemctl restart msl_aggregator
