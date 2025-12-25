import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch
import can

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import VolvoCracker, CMD_UNLOCK_REPLY

class TestCrackerLogic(unittest.TestCase):
    def setUp(self):
        # Mock the session file to avoid cluttering local dir
        self.patcher = patch('cracker.SESSION_FILE', 'test_cracker_session.json')
        self.patcher.start()
        self.cracker = VolvoCracker()
        self.cracker.bus = MagicMock()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists('test_cracker_session.json'):
            os.remove('test_cracker_session.json')

    def test_brute_force_success(self):
        # We want to test that if the Mock CAN returns a success reply, 
        # the brute force stops and returns the PIN.
        
        target_pin_suffix = [0x00, 0x01, 0x23] # Index 123
        target_index = 123
        
        # Configure Mock recv
        # We want it to return None for first 122 calls, then success for 123rd
        def mock_recv(timeout=0):
            if mock_recv.call_count == target_index:
                # Return success message
                # Message(arbitration_id=..., data=[CEM_ID, 0xB9, 0x00...])
                msg = MagicMock(spec=can.Message)
                msg.data = [self.cracker.cem_id, CMD_UNLOCK_REPLY, 0x00]
                return msg
            mock_recv.call_count += 1
            return None
        
        mock_recv.call_count = 0
        self.cracker.bus.recv.side_effect = mock_recv
        
        start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
        found_pin = self.cracker.brute_force(start_pin, start_index=0)
        
        self.assertIsNotNone(found_pin)
        self.assertEqual(found_pin[3:], target_pin_suffix)
        self.assertEqual(self.cracker.bus.send.call_count, target_index + 1)

    def test_brute_force_resume_behavior(self):
        # Verify it starts from start_index
        self.cracker.bus.recv.return_value = None
        start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
        
        # Only run a few iterations by patching the loop range or just using a high start_index
        # Actually, let's just check if it calls send with the right data first
        
        self.cracker.brute_force(start_pin, start_index=999990) # Near the end
        
        # Check the last call data
        last_call_args = self.cracker.bus.send.call_args_list[-1]
        msg = last_call_args[0][0]
        # 999999 should be [99, 99, 99] in BCD? 
        # No, 999999 / 10000 = 99. Rem = 9999. 9999 / 100 = 99. Rem = 99.
        # So [BCD(99), BCD(99), BCD(99)]
        self.assertEqual(msg.data[2+self.cracker.shuffle[3]], 0x99)
        self.assertEqual(msg.data[2+self.cracker.shuffle[4]], 0x99)
        self.assertEqual(msg.data[2+self.cracker.shuffle[5]], 0x99)

if __name__ == '__main__':
    unittest.main()
