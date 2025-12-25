#!/usr/bin/env python3
import can
import time
import random
import threading
import signal
import sys
from flask import Flask, jsonify

# Constants matching cracker.py
REQ_ID = 0x000FFFFE
CMD_UNLOCK = 0xBE
CMD_UNLOCK_REPLY = 0xB9
HS_REPLY_ID = 0x00000003

class VolvoCEMSim:
    def __init__(self, channel='vcan0', pin=None, pn=8690719):
        self.channel = channel
        self.secret_pin = pin or [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]
        self.pn = pn
        self.running = True
        self.bus = None
        
        # Timing attack simulation parameters
        self.base_latency = 0.002  # 2ms base
        self.jitter = 0.0005       # 0.5ms jitter
        self.match_penalty = 0.003 # 3ms extra if prefix matches

        # Flask Health Check
        self.flask_app = Flask(__name__)
        self.flask_app.add_url_rule('/health', 'health', self.health_check)
        self.flask_thread = threading.Thread(target=self.run_flask, daemon=True)

    def run_flask(self):
        self.flask_app.run(host='0.0.0.0', port=5001)

    def health_check(self):
        return jsonify({"status": "ok"})

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] [CEM-SIM] {msg}")

    def get_pn_frames(self, node_id):
        # f0: [0xCB, node, 0xB9, 0xF0, 0x00, BCD1, BCD2, BCD3]
        # f1: [0x00, BCD4, ...]
        pn_str = str(self.pn).zfill(8)
        bcd = [int(pn_str[i:i+2], 16) for i in range(0, 8, 2)] # This is a simplification of BCD
        # Correct BCD for 8690719: [0x08, 0x69, 0x07, 0x19]
        b1 = (int(pn_str[0]) << 4) | int(pn_str[1])
        b2 = (int(pn_str[2]) << 4) | int(pn_str[3])
        b3 = (int(pn_str[4]) << 4) | int(pn_str[5])
        b4 = (int(pn_str[6]) << 4) | int(pn_str[7])
        
        f0 = [0xCB, node_id, 0xB9, 0xF0, 0x00, b1, b2, b3]
        f1 = [0x00, b4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        return f0, f1

    def run(self):
        self.flask_thread.start()
        try:
            self.bus = can.interface.Bus(self.channel, interface='socketcan')
            self.log(f"Started on {self.channel} with PIN {self.secret_pin}")
        except Exception as e:
            self.log(f"Failed to open {self.channel}: {e}")
            return

        while self.running:
            msg = self.bus.recv(timeout=0.5)
            if not msg: continue
            
            if msg.arbitration_id == REQ_ID:
                data = msg.data
                if len(data) < 2: continue
                
                node_id = data[0]
                cmd = data[1]
                
                if cmd == CMD_UNLOCK:
                    received_pin = list(data[2:8])
                    
                    # Calculate Latency for Timing Attack simulation
                    latency = self.base_latency + random.uniform(0, self.jitter)
                    
                    # Add penalty for matching prefixes
                    match_count = 0
                    for i in range(3):
                        if received_pin[i] == self.secret_pin[i]:
                            match_count += 1
                        else:
                            break
                    
                    latency += (match_count * self.match_penalty)
                    
                    # Simulate processing time
                    time.sleep(latency)
                    
                    success = (received_pin == self.secret_pin)
                    reply_data = [node_id, CMD_UNLOCK_REPLY, 0x00 if success else 0x01, 0, 0, 0, 0, 0]
                    
                    reply = can.Message(
                        arbitration_id=HS_REPLY_ID,
                        data=reply_data,
                        is_extended_id=True
                    )
                    self.bus.send(reply)
                    
                    if success:
                        self.log(f"Unlock SUCCESS with PIN {received_pin}")
                
                elif data[2] == 0xB9 and data[3] == 0xF0: # P/N Request
                    f0_data, f1_data = self.get_pn_frames(node_id)
                    
                    self.bus.send(can.Message(arbitration_id=HS_REPLY_ID, data=f0_data, is_extended_id=True))
                    time.sleep(0.01)
                    self.bus.send(can.Message(arbitration_id=HS_REPLY_ID, data=f1_data, is_extended_id=True))
                    self.log(f"P/N Request handled for node {hex(node_id)}")

    def stop(self):
        self.running = False
        if self.bus:
            self.bus.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="vcan0")
    parser.add_argument("--pin", default="123456789012", help="6-byte PIN in hex")
    parser.add_argument("--pn", type=int, default=8690719)
    args = parser.parse_args()
    
    pin = [int(args.pin[i:i+2], 16) for i in range(0, 12, 2)]
    
    sim = VolvoCEMSim(channel=args.channel, pin=pin, pn=args.pn)
    
    def signal_handler(sig, frame):
        sim.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    sim.run()
