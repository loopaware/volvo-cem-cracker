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

    def test_timing_attack_simulation(self):
        cracker = VolvoCracker(channel='test_mock_timing')
        cracker.bus = MagicMock()
        
        # Simulating Latency
        # Prefix match adds 5ms latency
        def mocked_recv(timeout=0):
            # We use the call count or some state to return different latencies
            pass # We'll use a more targeted approach

        def get_latency_reply(received_pin):
            latency = 0.002 # Base 2ms
            # If first byte matches 0x12
            if received_pin[0] == SECRET_PIN[0]:
                latency += 0.005 # Match penalty
            
            reply_data = [self.cracker_node, CMD_UNLOCK_REPLY, 0x01, 0, 0, 0, 0, 0]
            reply = can.Message(arbitration_id=0x00000003, is_extended_id=True, data=reply_data)
            # Simulate the delay by adjusting the timestamp or just returning it
            reply.timestamp = time.time() + latency 
            return reply

        self.cracker_node = 0x50
        
        # Mocking timing attack loop
        with patch('time.time') as mock_time:
            # We need a way to make time flow
            current_time = [1000.0]
            def get_now():
                t = current_time[0]
                current_time[0] += 0.001 # Increment slightly
                return t
            mock_time.side_effect = get_now
            
            # Setup cracker for mock
            cracker.bus.send = MagicMock()
            
            def side_effect_recv(timeout=0):
                # Look at the last sent PIN (hard to get from here easily, so we just mock the result)
                return None # The real logic uses timestamps
            
            # This is complex to mock perfectly because it relies on real-world timing.
            # Instead, let's mock 'unlock_attempt_timing' directly to verify the logic 
            # that CHOOSES the candidates based on latency.
            
            def mock_unlock_timing(pin):
                lat = 0.002
                if pin[0] == SECRET_PIN[0]:
                    lat += 0.005
                return False, lat
            
            cracker.unlock_attempt_timing = mock_unlock_timing
            
            candidates = cracker.crack_timing(known_bytes=0)
            
            # The top candidate should have 0x12 as the first byte
            self.assertEqual(candidates[0][0], 0x12)

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
