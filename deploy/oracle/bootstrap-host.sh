#!/usr/bin/env bash
set -euo pipefail

role="${1:-}"
if [[ "$role" != "api" && "$role" != "worker" ]]; then
    echo "Usage: $0 <api|worker>" >&2
    exit 2
fi

swap_size_mb=2048
if [[ "$role" == "api" ]]; then
    swap_size_mb=4096
fi

if ! swapon --show=NAME --noheadings | grep -qx '/swapfile'; then
    if [[ ! -f /swapfile ]]; then
        sudo dd if=/dev/zero of=/swapfile bs=1M count="$swap_size_mb" status=progress
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
    fi
    sudo swapon /swapfile
fi

if ! grep -q '^/swapfile ' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    ca-certificates \
    curl \
    libffi-dev \
    libssl-dev \
    pkg-config \
    python3-dev \
    python3-pip \
    python3-venv

if [[ "$role" == "api" ]]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y caddy
fi

if ! id fleetopt >/dev/null 2>&1; then
    sudo useradd --system --home-dir /opt/fleetopt --create-home --shell /usr/sbin/nologin fleetopt
fi

sudo install -d -m 0750 -o fleetopt -g fleetopt /opt/fleetopt/backend
sudo install -d -m 0750 -o root -g fleetopt /etc/fleetopt

echo "FleetOpt $role host bootstrap complete"
