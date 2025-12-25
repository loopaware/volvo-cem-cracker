"""
Enhanced integration tests for Volvo CEM Cracker.

Comprehensive integration tests covering:
- Full cracking workflow from start to finish
- Resume functionality after partial completion
- Multiple CEM configuration scenarios
- Error recovery and continuation
"""

import unittest
import sys
import os
import time
import json
import tempfile
from unittest.mock import MagicMock, patch
import can

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import VolvoCracker, REQ_ID, CMD_UNLOCK, CMD_UNLOCK_REPLY
from config import BCD_TABLE, SHUFFLE_ORDERS


class TestFullWorkflowIntegration(unittest.TestCase):
    """Integration tests for full cracking workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_session_file = os.path.join(self.temp_dir, "session.json")
        
        # Patch session file location
        self.session_patcher = patch('cracker.SESSION_FILE', self.test_session_file)
        self.session_patcher.start()
        
        self.cracker = VolvoCracker(channel='test')
        self.cracker.bus = MagicMock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.session_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_crack_workflow_mock(self):
        """Test complete cracking workflow with mocked CAN."""
        # Configure cracker
        self.assertTrue(self.cracker.configure_for_cem(8690719))
        self.assertEqual(self.cracker.baud, 500000)
        
        # Set up mock to succeed at known index
        target_index = 500  # PIN suffix at index 500
        def mock_recv(timeout=0):
            if mock_recv.call_count == target_index:
                msg = MagicMock(spec=can.Message)
                msg.data = [self.cracker.cem_id, CMD_UNLOCK_REPLY, 0x00]
                return msg
            mock_recv.call_count += 1
            return None
        
        mock_recv.call_count = 0
        self.cracker.bus.recv.side_effect = mock_recv
        self.cracker.bus.send = MagicMock()
        
        # Run brute force
        start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
        found = self.cracker.brute_force(start_pin, start_index=0)
        
        # Verify success
        self.assertIsNotNone(found)
        self.assertEqual(found[3], BCD_TABLE[target_index // 10000 % 100])
        self.assertEqual(found[4], BCD_TABLE[target_index // 100 % 100])
        self.assertEqual(found[5], BCD_TABLE[target_index % 100])
    
    def test_resume_workflow(self):
        """Test resume from saved session."""
        # Create a saved session
        self.cracker.save_session(5000, [0x12, 0x34, 0x56, 0, 0, 0], [])
        
        # Load session
        loaded_index, loaded_fixed, loaded_queue = self.cracker.load_session()
        
        # Verify rewind logic
        self.assertEqual(loaded_index, 4500)  # 5000 - 500
        self.assertEqual(loaded_fixed, [0x12, 0x34, 0x56, 0, 0, 0])
        
        print(f"Resume test: Would resume from index {loaded_index}")
    
    def test_error_recovery_workflow(self):
        """Test error recovery during cracking."""
        # Set up mock to fail then succeed
        def mock_send(msg):
            if mock_send.fail_count > 0:
                mock_send.fail_count -= 1
                raise can.CanError("Simulated error")
        
        mock_send.fail_count = 3  # Fail first 3 sends
        self.cracker.bus.send.side_effect = mock_send
        self.cracker.bus.recv.return_value = None
        
        # Should handle errors gracefully without crashing
        start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
        
        # This should not raise an exception
        try:
            # Run for a few iterations
            self.cracker.brute_force(start_pin, start_index=0)
        except Exception as e:
            self.fail(f"Error recovery failed: {e}")


class TestCEMConfigurationIntegration(unittest.TestCase):
    """Integration tests for CEM configuration scenarios."""
    
    def test_p1_cem_configuration(self):
        """Test P1 CEM configuration."""
        cracker = VolvoCracker()
        
        p1_pns = [8690719, 8690720, 8690721, 8690722]
        for pn in p1_pns:
            with self.subTest(pn=pn):
                self.assertTrue(cracker.configure_for_cem(pn))
                self.assertEqual(cracker.baud, 500000)
    
    def test_p2_cem_l_configuration(self):
        """Test P2 CEM-L configuration."""
        cracker = VolvoCracker()
        
        p2_l_pns = [30786889, 30682981, 30786475]
        for pn in p2_l_pns:
            with self.subTest(pn=pn):
                self.assertTrue(cracker.configure_for_cem(pn))
                self.assertEqual(cracker.baud, 500000)
                self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[1])
    
    def test_p2_cem_brick_configuration(self):
        """Test P2 CEM-Brick configuration."""
        cracker = VolvoCracker()
        
        p2_brick_pns = [8645716, 8645719, 8688434]
        for pn in p2_brick_pns:
            with self.subTest(pn=pn):
                self.assertTrue(cracker.configure_for_cem(pn))
                self.assertEqual(cracker.baud, 250000)
    
    def test_unknown_cem_fallback(self):
        """Test fallback for unknown CEM."""
        cracker = VolvoCracker()
        
        # Unknown PN should use defaults
        result = cracker.configure_for_cem(9999999)
        self.assertFalse(result)
        self.assertEqual(cracker.baud, 500000)
        self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[0])


class TestSessionRecoveryIntegration(unittest.TestCase):
    """Integration tests for session recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_file = os.path.join(self.temp_dir, "session.json")
        self.backup_file = os.path.join(self.temp_dir, "session.bak")
        
        # Patch session file location
        self.session_patcher = patch('cracker.SESSION_FILE', self.session_file)
        self.session_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.session_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_recovery_from_corrupted_session(self):
        """Test recovery when primary session is corrupted."""
        # We need to test the raw SessionManager
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Create a valid session first
        cracker.save_session(5000, [0x12, 0x34, 0x56, 0, 0, 0], [])
        
        # Now manually corrupt the file
        with open(self.session_file, "w") as f:
            f.write("corrupted data")
        
        # Load should handle gracefully (return None values)
        loaded_index, loaded_fixed, loaded_queue = cracker.load_session()
        
        # Should return None for corrupted session
        self.assertIsNone(loaded_index)
    
    def test_recovery_from_empty_session(self):
        """Test recovery when session file is empty."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Create empty file
        with open(self.session_file, "w") as f:
            f.write("")
        
        # Should handle gracefully
        loaded_index, loaded_fixed, loaded_queue = cracker.load_session()
        
        self.assertIsNone(loaded_index)
    
    def test_concurrent_session_access(self):
        """Test session behavior with rapid save/load cycles."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Rapid save/load cycles
        for i in range(10):
            cracker.save_session(i * 1000, [i, 0, 0, 0, 0, 0], [])
            loaded_index, _, _ = cracker.load_session()
            # Should not crash
            self.assertIsNotNone(loaded_index)


if __name__ == '__main__':
    unittest.main()
