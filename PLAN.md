# Plan: Port Volvo CEM Cracker to Raspberry Pi

## Objective
Port the functionality of `volvo-cem-cracker.ino` to a Python-based solution running on a Raspberry Pi Zero 2 W with a Waveshare CAN HAT. Deploy using Ansible.

## Challenges
*   **Timing Accuracy**: The original Arduino code uses a hardware cycle counter and direct GPIO polling. Linux/Python is less precise.
*   **Mitigation**: Implement `socketcan` timestamps and a fallback Brute Force mode.
*   **Deployment**: Must be automated via Ansible for the remote Pi.

## Architecture
*   **Script**: `volvo_cracker.py` (Main logic).
*   **Monitor**: `oled_monitor.py` (Display status).
*   **Service**: `volvo-cracker.service` (Systemd unit).

## Deployment (Ansible)
*   **Target**: `10.107.116.1` (User: `uzanto`).
*   **Playbook**: `deploy/playbook.yml`.
*   **Tasks**:
    1.  Install system dependencies (`can-utils`, `i2c-tools`, `python3-pip`, `python3-venv`).
    2.  Enable I2C and SPI (if not enabled).
    3.  Setup CAN interface (Waveshare driver overlays).
    4.  Create application directory (`/opt/volvo-cracker` or home dir).
    5.  Install Python dependencies (`python-can`, `adafruit-circuitpython-ssd1306`, `RPi.GPIO`, etc.).
    6.  Deploy code.
    7.  Install and start Systemd service.

## Steps
1.  **Code Porting**: `volvo_cracker.py` (Completed).
2.  **Ansible Setup**:
    *   Create `deploy/inventory`.
    *   Create `deploy/playbook.yml`.
3.  **Documentation**: Update `README.md`.
4.  **Execution**: Run Ansible playbook.