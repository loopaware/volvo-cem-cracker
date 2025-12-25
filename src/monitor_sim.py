#!/usr/bin/env python3
import time
from PIL import Image, ImageDraw, ImageFont
import subprocess
import os
import sys

# Simulation support: use luma.emulator if running headlessly or for tests
try:
    from luma.emulator.device import capture
    from luma.core.render import canvas
    SIM_MODE = True
except ImportError:
    SIM_MODE = False

# Fallback for RPi.GPIO
try:
    import RPi.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BCM = 11
        IN = 1
        PUD_UP = 22
        LOW = 0
        HIGH = 1
        def setmode(self, mode): pass
        def setup(self, pin, mode, pull_up_down=None): pass
        def input(self, pin): return 1 # Always high (not pressed)
    GPIO = MockGPIO()

LOG_FILE = "crack.log"

class VolvoMonitorSim:
    def __init__(self, mode='capture', output_dir='docs/images/screens'):
        self.width = 128
        self.height = 64
        self.output_dir = output_dir
        self.cold_weather_delay = 0 # In seconds
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        if SIM_MODE:
            self.device = capture(width=self.width, height=self.height, mode="1", scale=1, file_template=f"{output_dir}/screen_{{0:03d}}.png")
        else:
            self.device = None

        self.font = ImageFont.load_default()
        self.frame_count = 0

    def set_cold_weather(self, enabled=True):
        # Proposal says 500ms delay for cold weather
        self.cold_weather_delay = 0.5 if enabled else 0

    def get_ip(self):
        return "127.0.0.1 (SIM)"

    def get_last_line(self, filepath):
        try:
            if not os.path.exists(filepath): return "Waiting..."
            cmd = f"tail -n 1 {filepath}"
            line = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            return line[:20] + "..." if len(line) > 20 else line
        except: return "Read Error"

    def check_success(self, filepath):
        try:
            if not os.path.exists(filepath): return None
            cmd = f"grep -a 'FOUND PIN' {filepath}"
            result = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            if "FOUND PIN" in result: return result.split(":")[-1].strip()
        except: return None
        return None

    def render(self):
        if self.cold_weather_delay > 0:
            time.sleep(self.cold_weather_delay)
            
        with canvas(self.device) as draw:
            ip = self.get_ip()
            pin = self.check_success(LOG_FILE)
            
            if pin:
                draw.text((0, 0),  "!!! SUCCESS !!!", font=self.font, fill=255)
                draw.text((0, 15), "PIN FOUND:", font=self.font, fill=255)
                draw.text((10, 35), pin, font=self.font, fill=255)
                draw.text((0, 50), "Take a photo!", font=self.font, fill=255)
            else:
                status = self.get_last_line(LOG_FILE)
                draw.text((0, 0), "VOLVO CRACKER", font=self.font, fill=255)
                draw.text((0, 12), f"IP: {ip}", font=self.font, fill=255)
                draw.text((0, 25), "-" * 20, font=self.font, fill=255)
                draw.text((0, 36), "Status:", font=self.font, fill=255)
                draw.text((0, 48), status, font=self.font, fill=255)
        
        self.frame_count += 1

    def run_once(self):
        self.render()

if __name__ == "__main__":
    mon = VolvoMonitorSim()
    while True:
        mon.run_once()
        time.sleep(2)