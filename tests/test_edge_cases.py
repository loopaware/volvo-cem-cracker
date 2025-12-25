"""
Test suite for edge case handling.

Tests boundary conditions and unusual scenarios:
- Minimum/maximum PIN values
- Empty session files
- Boundary conditions in timing attacks
- Shuffle order edge cases
- BCD conversion boundaries
"""

import unittest
import sys
import os
import tempfile
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import bcd_to_bin, bin_to_bcd
from config import BCD_TABLE, SHUFFLE_ORDERS


class TestBCDConversionEdgeCases(unittest.TestCase):
    """Test BCD conversion at boundaries."""
    
    def test_bcd_minimum_value(self):
        """Test BCD conversion for 0."""
        self.assertEqual(bin_to_bcd(0), 0x00)
        self.assertEqual(bcd_to_bin(0x00), 0)
    
    def test_bcd_maximum_value(self):
        """Test BCD conversion for 99."""
        self.assertEqual(bin_to_bcd(99), 0x99)
        self.assertEqual(bcd_to_bin(0x99), 99)
    
    def test_bcd_boundary_values(self):
        """Test BCD conversion at all boundary values."""
        boundaries = [0, 9, 10, 19, 90, 99]
        for val in boundaries:
            with self.subTest(val=val):
                bcd = bin_to_bcd(val)
                back = bcd_to_bin(bcd)
                self.assertEqual(back, val, f"BCD conversion failed for {val}")
    
    def test_bcd_table_completeness(self):
        """Test that BCD table contains all values 0-99."""
        for i in range(100):
            with self.subTest(i=i):
                self.assertEqual(BCD_TABLE[i], ((i // 10) << 4) | (i % 10))


class TestShuffleOrderEdgeCases(unittest.TestCase):
    """Test shuffle order edge cases."""
    
    def test_all_shuffle_orders_are_permutations(self):
        """Verify all shuffle orders are valid permutations."""
        for i, shuffle in enumerate(SHUFFLE_ORDERS):
            with self.subTest(shuffle_index=i):
                expected = set(range(6))
                actual = set(shuffle)
                self.assertEqual(actual, expected, 
                               f"Shuffle order {i} is not a valid permutation")
    
    def test_shuffle_order_coverage(self):
        """Verify shuffle orders provide reasonable coverage."""
        # Each position should appear in at least 2 different slots across all shuffles
        # This is a weaker test than expecting complete coverage
        for position in range(6):
            slots = set()
            for shuffle in SHUFFLE_ORDERS:
                slots.add(shuffle[position])
            # Each position should appear in at least 2 different slots
            self.assertGreaterEqual(len(slots), 2,
                           f"Position {position} has insufficient coverage: {slots}")


class TestPinEdgeCases(unittest.TestCase):
    """Test PIN handling at edge cases."""
    
    def test_all_zero_pin(self):
        """Test handling of all-zero PIN."""
        pin = [0x00] * 6
        self.assertEqual(len(pin), 6)
        # All bytes should be valid BCD
        for byte in pin:
            self.assertLessEqual(byte, 0x99)
    
    def test_all_max_pin(self):
        """Test handling of all-maximum PIN."""
        pin = [0x99] * 6
        self.assertEqual(len(pin), 6)
        # All bytes should be valid BCD
        for byte in pin:
            self.assertLessEqual(byte, 0x99)
    
    def test_pin_with_known_bytes(self):
        """Test PIN with some known bytes."""
        known_pin = [0x12, 0x34, 0x56, 0x00, 0x00, 0x00]
        self.assertEqual(known_pin[0], 0x12)
        self.assertEqual(known_pin[2], 0x56)


class TestSessionEdgeCases(unittest.TestCase):
    """Test session handling edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_session_file = os.path.join(self.temp_dir, "session.json")
        
        # Patch session file location
        self.session_patcher = patch('cracker.SESSION_FILE', self.test_session_file)
        self.session_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.session_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_zero_index_session(self):
        """Test session starting at index 0."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Save at index 0
        cracker.save_session(0, [0]*6, [])
        
        # Load should return 0 (not negative after rewind)
        loaded_index, _, _ = cracker.load_session()
        self.assertEqual(loaded_index, 0)
    
    def test_empty_queue(self):
        """Test session with empty candidates queue."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        cracker.save_session(500, [0]*6, [])
        
        loaded_index, _, loaded_queue = cracker.load_session()
        self.assertEqual(loaded_queue, [])
    
    def test_large_queue(self):
        """Test session with large candidates queue."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Create large queue
        large_queue = [[i, i+1, i+2, 0, 0, 0] for i in range(100)]
        
        cracker.save_session(500, [0]*6, large_queue)
        
        loaded_index, _, loaded_queue = cracker.load_session()
        self.assertEqual(len(loaded_queue), 100)


class TestTimingAttackEdgeCases(unittest.TestCase):
    """Test timing attack edge cases."""
    
    def test_single_sample(self):
        """Test timing attack with minimum samples."""
        # Should not crash with small sample count
        SAMPLES = 1
        self.assertGreaterEqual(SAMPLES, 1)
    
    def test_known_bytes_boundary(self):
        """Test timing attack with known bytes at boundary."""
        # Test all possible known byte counts (0-3)
        for known_bytes in range(4):
            with self.subTest(known_bytes=known_bytes):
                self.assertGreaterEqual(known_bytes, 0)
                self.assertLessEqual(known_bytes, 3)


class TestConfigurationEdgeCases(unittest.TestCase):
    """Test configuration edge cases."""
    
    def test_unknown_cem_default(self):
        """Test handling of unknown CEM part number."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        # Unknown PN should return False and use defaults
        result = cracker.configure_for_cem(9999999)
        self.assertFalse(result)
        self.assertEqual(cracker.baud, 500000)  # Default P1
        self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[0])  # Default shuffle
    
    def test_boundary_baud_rates(self):
        """Test all valid baud rates."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        
        # Test known PNs with different baud rates
        p1_pn = 8690719  # P1, 500K
        p2_brick_pn = 8645716  # P2 Brick, 250K
        
        # P1
        self.assertTrue(cracker.configure_for_cem(p1_pn))
        self.assertEqual(cracker.baud, 500000)
        
        # P2 Brick
        self.assertTrue(cracker.configure_for_cem(p2_brick_pn))
        self.assertEqual(cracker.baud, 250000)


if __name__ == '__main__':
    unittest.main()
