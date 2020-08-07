#!/usr/bin/bash -u

# Capture Vegeta
wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
tar -xzf vegeta-12.8.3-linux-amd64.tar.gz

venv_path=${VENV:-/tmp/quay_venv}
python3 -m venv $venv_path
source $venv_path/bin/activate

# Install SNAFU
cd /tmp
git clone https://github.com/cloud-bulldozer/snafu
cd snafu
python setup.py develop

# Install Touchstone
cd /tmp
git clone https://github.com/cloud-bulldozer/touchstone
cd touchstone
python setup.py develop

# Clone Backpack for metadata capture
cd /tmp
git clone https://github.com/cloud-bulldozer/backpack
