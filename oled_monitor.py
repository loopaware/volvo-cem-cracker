import time
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import subprocess
import os
import RPi.GPIO as GPIO

# --- SETUP ---
# Create I2C interface
i2c = busio.I2C(board.SCL, board.SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Clear display
disp.fill(0)
disp.show()

width = disp.width
height = disp.height
image = Image.new("1", (width, height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

#LOG_FILE = "volvo-cem-cracker/crack.log"
LOG_FILE = "/home/uzanto/volvo-cem-cracker/crack.log"

def get_ip():
    try:
        cmd = "hostname -I | cut -d' ' -f1"
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except:
        return "No Wifi"

def get_last_line(filepath):
    try:
        if not os.path.exists(filepath):
            return "Waiting..."
        # Read the file and get the last line
        cmd = "tail -n 1 " + filepath
        line = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        if len(line) > 20: 
            return line[:20] + "..." # Truncate if too long
        return line
    except:
        return "Read Error"

def check_success(filepath):
    # Grep the file for the winning phrase
    try:
        if not os.path.exists(filepath):
            return None
        cmd = "grep -a 'FOUND PIN' " + filepath
        result = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        if "FOUND PIN" in result:
            # Extract just the pin (everything after colon)
            return result.split(":")[-1].strip()
    except subprocess.CalledProcessError:
        return None # Grep found nothing
    return None

# Setup Shutdown Button on GPIO 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

while True:
    # Power off button
    # Check for button press (Low = Pressed)
    if GPIO.input(21) == GPIO.LOW:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        draw.text((0, 20), "SHUTTING DOWN...", font=font, fill=255)
        disp.image(image)
        disp.show()
        time.sleep(2)
        os.system("shutdown now -h")

    # Drawing
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    
    ip = get_ip()
    pin = check_success(LOG_FILE)

    if pin:
        # --- SUCCESS SCREEN ---
        draw.text((0, 0),  "!!! SUCCESS !!!", font=font, fill=255)
        draw.text((0, 15), "PIN FOUND:", font=font, fill=255)
        # Draw PIN larger/centered if possible, standard font for now
        draw.text((10, 35), pin, font=font, fill=255)
        draw.text((0, 50), "Take a photo!", font=font, fill=255)
        
    else:
        # --- MONITOR SCREEN ---
        status = get_last_line(LOG_FILE)
        
        draw.text((0, 0), "VOLVO CRACKER", font=font, fill=255)
        draw.text((0, 12), f"IP: {ip}", font=font, fill=255)
        draw.text((0, 25), "-" * 20, font=font, fill=255)
        draw.text((0, 36), "Status:", font=font, fill=255)
        draw.text((0, 48), status, font=font, fill=255)

    disp.image(image)
    disp.show()
    time.sleep(2)