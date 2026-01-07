#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root (one level up from scripts/)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Paths
SERVICE_FILE="$PROJECT_ROOT/service/wonderbot.service"
SYSTEMD_TARGET="/etc/systemd/system/wonderbot.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

echo "Installing systemd service..."
echo "  Source: $SERVICE_FILE"
echo "  Target: $SYSTEMD_TARGET"

# Remove old service file if it exists
sudo rm -f "$SYSTEMD_TARGET"

# Copy service file to systemd
sudo cp "$SERVICE_FILE" "$SYSTEMD_TARGET"

# Reload systemd daemon
sudo systemctl daemon-reload

echo "Service installed successfully!"
echo "To start the service, run: sudo systemctl start wonderbot"
echo "To enable on boot, run: sudo systemctl enable wonderbot"
