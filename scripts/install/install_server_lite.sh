#!/bin/bash

# Lightweight installation script for low-spec servers
echo "Starting lightweight installation..."

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install essential packages
echo "Installing essential packages..."
sudo apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    # Add other necessary packages here, excluding FFmpeg and Scrcpy.

# Mark video streaming features as unavailable
echo "Video streaming features are unavailable in this installation."

# Additional setup steps can be included here.

echo "Lightweight installation completed."