import unittest
import sys
import os
import json
import time
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import VolvoCracker

class TestResume(unittest.TestCase):
    def setUp(self):
        self.test_session_file = "test_session.json"
        # Patch the SESSION_FILE constant in the module
        self.patcher = patch('cracker.SESSION_FILE', self.test_session_file)
        self.patcher.start()
        
        self.cracker = VolvoCracker()
        # Mock bus to avoid errors during init if it tries to touch CAN
        self.cracker.bus = MagicMock()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_session_file):
            os.remove(self.test_session_file)
        if os.path.exists(self.test_session_file + ".tmp"):
            os.remove(self.test_session_file + ".tmp")

    def test_save_and_load(self):
        index = 1000
        fixed_bytes = [1, 2, 3, 0, 0, 0]
        queue = [[1, 2, 3, 0, 0, 0], [4, 5, 6, 0, 0, 0]]
        
        # Save
        self.cracker.save_session(index, fixed_bytes, queue)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.test_session_file))
        
        # Load
        loaded_index, loaded_fixed, loaded_queue = self.cracker.load_session()
        
        # Check rewind logic (should be index - 500)
        self.assertEqual(loaded_index, 500)
        self.assertEqual(loaded_fixed, fixed_bytes)
        self.assertEqual(loaded_queue, queue)

    def test_load_no_file(self):
        idx, fixed, queue = self.cracker.load_session()
        self.assertIsNone(idx)
        self.assertIsNone(fixed)
        self.assertEqual(queue, [])

    def test_rewind_clamping(self):
        # Test that we don't rewind below 0
        index = 100
        self.cracker.save_session(index, [], [])
        loaded_index, _, _ = self.cracker.load_session()
        self.assertEqual(loaded_index, 0)

if __name__ == '__main__':
    unittest.main()
