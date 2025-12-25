# Raspberry Pi Zero (v1.3) Hardware Specifications & Optimization Guide

## Hardware Overview
*   **Model**: Raspberry Pi Zero v1.3 (No Wi-Fi, Camera Port version)
*   **SoC**: Broadcom BCM2835
*   **CPU**: Single-core ARM1176JZF-S (ARMv6) @ 1GHz (Default)
*   **GPU**: VideoCore IV @ 250MHz
*   **RAM**: 512MB LPDDR2 (Package-on-Package / PoP)
*   **Architecture**: `armel` (Debian) / `armv6l` (Linux Kernel)

## Critical Constraints
1.  **Single Core**: The CPU has only one core. Multiprocessing will not provide parallelism. The main cracker loop must yield for network/OS tasks, or run at a very high priority while "nice-ing" background tasks.
2.  **Memory Bandwidth**: The 512MB RAM is shared with the GPU. High-resolution display updates can steal bandwidth from the CPU.
3.  **Instruction Set**: Code compiled for ARMv7 (`armhf`) will **crash** with "Illegal Instruction". We must use software compiled for ARMv6 (`armel` or `raspbian`).

## Overclocking Profile (Stable with Heatsink)
To squeeze maximum performance (~10-15% gain) for the brute-force loop, apply these settings to `/boot/config.txt`.
**WARNING**: Requires a passive heatsink to prevent thermal throttling.

```ini
# Pi Zero v1.3 Performance Profile
arm_freq=1085
gpu_freq=530
over_voltage=2
core_freq=515
sdram_freq=533
over_voltage_sdram=1
force_turbo=0 # Keep at 0 to avoid voiding warranty bits, though risk remains
```

## Software Optimization Strategy
1.  **Python Interpreter**: Use `pypy3` if possible. The JIT compiler is significantly faster for the tight arithmetic loops in `cracker.py` than standard CPython.
2.  **Process Priority**: Run the cracker service with `Nice=-19` to preempt other processes.
3.  **Display Logic**: Limit OLED refresh rate to 1-2fps to reduce I2C/SPI interrupts and context switching.
