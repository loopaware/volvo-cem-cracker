import can
import logging
import time
from .config import REQ_ID, CEM_HS_ID, CEM_LS_ID
from .utils import bcd_to_bin

def setup_can(channel, bitrate):
    logging.info(f"Initializing CAN on {channel} @ {bitrate}...")
    try:
        # Add filters to ignore noise
        filters = [
            {"can_id": 0x00000003, "can_mask": 0x1FFFFFFF, "extended": True}, # HS Reply
            {"can_id": 0x00000005, "can_mask": 0x1FFFFFFF, "extended": True}, # LS Reply
            {"can_id": 0x03, "can_mask": 0x7FF, "extended": False},           # Std ID Reply?
        ]
        
        bus = can.interface.Bus(
            channel=channel, 
            interface='socketcan',
            bitrate=bitrate,
            can_filters=filters
        )
        return bus
    except Exception as e:
        logging.error(f"Error initializing CAN: {e}")
        return None

def send_msg(bus, arbitration_id, data, is_extended=False):
    # Helper for non-critical messages
    msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended)
    try:
        bus.send(msg)
        return time.time()
    except can.CanError as e:
        logging.error(f"Send Error: {e}")
        return None

def read_part_number(bus):
    """Attempts to read CEM Part Number."""
    # Need to temporarily disable filters or add broadcast filter?
    # For simplicity, we just rely on the existing filters catching the reply (usually 0x00000003)
    
    target_ids = [CEM_HS_ID, CEM_LS_ID]
    
    for tid in target_ids:
        logging.info(f"Attempting to read P/N from Node {hex(tid)}...")
        req = [0xCB, tid, 0xB9, 0xF0, 0x00, 0x00, 0x00, 0x00]
        
        for _ in range(3):
            # Drain
            while bus.recv(timeout=0): pass
            
            send_msg(bus, REQ_ID, req, is_extended=True)
            
            start = time.time()
            frames = {}
            
            while time.time() - start < 1.0:
                msg = bus.recv(timeout=0.1)
                if not msg: continue
                
                d = msg.data
                if not d: continue

                if d[0] & 0x80: 
                    frames[0] = d
                elif (d[0] & 0x40) == 0: 
                    frames[1] = d
                    
                if 0 in frames and 1 in frames:
                    f0 = frames[0]
                    f1 = frames[1]
                    
                    pn = 0
                    pn = (pn * 100) + bcd_to_bin(f0[5])
                    pn = (pn * 100) + bcd_to_bin(f0[6])
                    pn = (pn * 100) + bcd_to_bin(f0[7])
                    pn = (pn * 100) + bcd_to_bin(f1[1])
                    
                    logging.info(f"Found Part Number: {pn}")
                    return pn
    return None
