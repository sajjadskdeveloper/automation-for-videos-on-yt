#!/bin/bash

# Update and install system dependencies
echo "Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip python3-venv git

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python requirements..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating application directories..."
mkdir -p uploads outputs downloads

echo "Setup complete! You can now run the server with:"
echo "./venv/bin/gunicorn -c gunicorn_config.py app:app"
