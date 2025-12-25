import unittest
import sys
import os
import time
import can
import json
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import VolvoCracker, REQ_ID, CMD_UNLOCK, CMD_UNLOCK_REPLY

SECRET_PIN = [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Patch SESSION_FILE
        self.patcher = patch('cracker.SESSION_FILE', 'test_int_session.json')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists('test_int_session.json'):
            os.remove('test_int_session.json')

    def test_full_flow_mocked_interaction(self):
        cracker = VolvoCracker(channel='test_mock')
        cracker.bus = MagicMock()
        
        # Simulating CEM Responses
        def mocked_recv(timeout=0):
            if not hasattr(mocked_recv, 'responses'):
                mocked_recv.responses = []
            
            if mocked_recv.responses:
                return mocked_recv.responses.pop(0)
            return None
        
        mocked_recv.responses = []
        cracker.bus.recv.side_effect = mocked_recv
        
        def mocked_send(msg):
            if msg.arbitration_id == REQ_ID:
                data = msg.data
                if data[2] == 0xB9 and data[3] == 0xF0: # P/N Request
                    # Reply with dummy P/N: 8690719 (P1)
                    # BCD: 08 69 07 19
                    f0 = can.Message(arbitration_id=0x00000003, is_extended_id=True, data=[0xCB, data[1], 0xB9, 0xF0, 0x00, 0x08, 0x69, 0x07])
                    f1 = can.Message(arbitration_id=0x00000003, is_extended_id=True, data=[0x00, 0x19, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                    mocked_recv.responses.extend([f0, f1])
                elif data[1] == CMD_UNLOCK:
                    received_pin = list(data[2:8])
                    reply_data = [data[0], CMD_UNLOCK_REPLY, 0x01, 0, 0, 0, 0, 0]
                    if received_pin == SECRET_PIN:
                        reply_data[2] = 0x00
                    
                    reply = can.Message(arbitration_id=0x00000003, is_extended_id=True, data=reply_data)
                    mocked_recv.responses.append(reply)

        cracker.bus.send.side_effect = mocked_send
        
        # 1. P/N Read
        pn = cracker.read_part_number()
        self.assertEqual(pn, 8690719)
        cracker.configure_for_cem(pn)
        
        # 2. Brute Force
        start_index = 789000
        start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
        
        found = cracker.brute_force(start_pin, start_index=start_index)
        self.assertEqual(found, SECRET_PIN)

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
