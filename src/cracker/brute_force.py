import logging
import time
import os
from ..config import BCD_TABLE, SESSION_FILE
from .unlock import unlock_attempt_fast

def check_power_sag():
    """
    Detects if the power rail is dipping (e.g. during engine cranking).
    In simulation: checks for a trigger file.
    In production: could check /sys/class/leds/led1/brightness (Pi Power LED)
    or a dedicated GPIO pin.
    """
    if os.path.exists("POWER_SAG.trigger"):
        return True
    return False

def save_session(index, fixed_bytes, candidates_queue=None):
    """
    Save cracking session to file.
    """
    try:
        state = {
            "timestamp": time.time(),
            "index": index,
            "fixed_bytes": fixed_bytes,
            "candidates_queue": candidates_queue or []
        }
        tmp_file = "session.json.tmp"
        with open(tmp_file, "w") as f:
            import json
            json.dump(state, f)
        os.replace(tmp_file, "session.json")
    except Exception as e:
        logging.error(f"Error saving session: {e}")

def brute_force(bus, tx_msg, cem_id, shuffle, start_pin, start_index=0, candidates_queue=None):
    logging.info(f"Starting Brute Force from index {start_index}...")
    
    current_pin = list(start_pin)
    total = 1000000
    start_t = time.time()
    SAVE_INTERVAL = 2000 
    
    for i in range(start_index, total):
        # --- VOLTAGE SAG / POWER FAIL CHECK ---
        # In a real Swedish winter, cranking can drop voltage.
        # We check a mock file or GPIO to simulate this.
        if check_power_sag():
            logging.warning("!!! VOLTAGE SAG DETECTED !!! Pausing for safety...")
            save_session(i, start_pin, candidates_queue)
            while check_power_sag():
                time.sleep(1)
            logging.info("Power stabilized. Resuming...")
            start_t = time.time() # Reset rate calc

        # Optimized iteration
        rem = i
        d1, rem = divmod(rem, 10000)
        d2, d3 = divmod(rem, 100)
        
        current_pin[3] = BCD_TABLE[d1]
        current_pin[4] = BCD_TABLE[d2]
        current_pin[5] = BCD_TABLE[d3]
        
        if i % SAVE_INTERVAL == 0:
            elapsed = time.time() - start_t
            rate = (i - start_index) / elapsed if elapsed > 0 else 0
            remaining = total - i
            eta = remaining / rate if rate > 0 else 0
            logging.info(f"Progress: {i}/{total} ({i/total*100:.1f}%) Rate: {rate:.1f}/s ETA: {eta/60:.1f}m - PIN: {current_pin}")
            save_session(i, start_pin, candidates_queue)
        
        if unlock_attempt_fast(bus, tx_msg, cem_id, shuffle, current_pin):
            logging.info(f"\n!!! FOUND PIN: {current_pin} !!!")
            if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
            return current_pin
            
    return None
