#!/bin/bash
# Volvo CEM Cracker - Runner Script
# Ensures CAN is up and starts the cracker in the virtualenv

CWD="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VENV_PYTHON="$CWD/venv/bin/python3"

# 1. Bring up CAN interface if it's down
if ! ip link show can0 | grep -q "UP"; then
    echo "Bringing up can0 interface..."
    sudo ip link set can0 up type can bitrate 500000
fi

# 2. Run the cracker
echo "Starting Volvo CEM Cracker..."
$VENV_PYTHON "$CWD/src/cracker.py"
