import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import bcd_to_bin, bin_to_bcd, CEM_PARAMS, SHUFFLE_ORDERS, VolvoCracker

class TestLogic(unittest.TestCase):
    def test_bcd_conversions(self):
        # Test 0-99
        for i in range(100):
            bcd = bin_to_bcd(i)
            # Higher nibble is tens, lower is units
            self.assertEqual(bcd, ((i // 10) << 4) | (i % 10))
            self.assertEqual(bcd_to_bin(bcd), i)

    def test_cem_configuration(self):
        cracker = VolvoCracker()
        
        # Test a known P1 P/N
        pn_p1 = 8690719
        self.assertTrue(cracker.configure_for_cem(pn_p1))
        self.assertEqual(cracker.baud, 500000)
        self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[0])
        
        # Test a known P2 CEM-L P/N
        pn_p2_l = 30786889
        self.assertTrue(cracker.configure_for_cem(pn_p2_l))
        self.assertEqual(cracker.baud, 500000)
        self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[1])

        # Test unknown P/N
        self.assertFalse(cracker.configure_for_cem(9999999))
        # Should default to P1 settings
        self.assertEqual(cracker.baud, 500000)
        self.assertEqual(cracker.shuffle, SHUFFLE_ORDERS[0])

if __name__ == '__main__':
    unittest.main()
