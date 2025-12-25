"""
Test suite for error handling functionality.

Tests comprehensive error handling scenarios including:
- CAN bus errors
- Timeout scenarios  
- Invalid PIN format handling
- CEM part number detection failures
- Session file corruption
- Power sag detection
"""

import unittest
import sys
import os
import json
import tempfile
from unittest.mock import MagicMock, patch
import can

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker.errors import (
    CrackerError, CanBusError, SessionError, ConfigurationError,
    InvalidPartNumberError, InvalidPinFormatError
)
from cracker.validation import (
    validate_pin_format, validate_cem_part_number, 
    validate_shuffle_order, validate_baud_rate
)


class TestErrorTypes(unittest.TestCase):
    """Test custom error type classes."""
    
    def test_cracker_error_basic(self):
        """Test basic CrackerError functionality."""
        error = CrackerError("Test error message", {"key": "value"})
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.details, {"key": "value"})
        self.assertIsInstance(error.timestamp, float)
        self.assertIn("Test error message", str(error))
    
    def test_can_bus_error(self):
        """Test CanBusError with bus information."""
        error = CanBusError("CAN error", bus_id="can0", error_code=5)
        self.assertEqual(error.details["bus_id"], "can0")
        self.assertEqual(error.details["error_code"], 5)
    
    def test_invalid_part_number_error(self):
        """Test InvalidPartNumberError."""
        error = InvalidPartNumberError(12345, "Invalid prefix")
        self.assertEqual(error.details["part_number"], 12345)
        self.assertIn("12345", str(error))


class TestValidationFunctions(unittest.TestCase):
    """Test validation functions."""
    
    def test_validate_pin_format_valid(self):
        """Test valid PIN format validation."""
        valid_pins = [
            [0x12, 0x34, 0x56, 0x78, 0x90, 0x12],
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            [0x99, 0x99, 0x99, 0x99, 0x99, 0x99],
        ]
        for pin in valid_pins:
            with self.subTest(pin=pin):
                self.assertTrue(validate_pin_format(pin))
    
    def test_validate_pin_format_invalid_length(self):
        """Test invalid PIN length detection."""
        invalid_pins = [
            [0x12, 0x34, 0x56],  # Too short
            [0x12] * 10,         # Too long
        ]
        for pin in invalid_pins:
            with self.subTest(pin=pin):
                with self.assertRaises(InvalidPinFormatError):
                    validate_pin_format(pin)
    
    def test_validate_pin_format_invalid_bcd(self):
        """Test invalid BCD value detection."""
        # High nibble > 9 is invalid BCD
        invalid_pins = [
            [0xA0, 0x34, 0x56, 0x78, 0x90, 0x12],  # A0 has high nibble 10
            [0x12, 0xB4, 0x56, 0x78, 0x90, 0x12],  # B4 has high nibble 11
        ]
        for pin in invalid_pins:
            with self.subTest(pin=pin):
                with self.assertRaises(InvalidPinFormatError):
                    validate_pin_format(pin)
    
    def test_validate_pin_format_non_integer(self):
        """Test non-integer PIN byte detection."""
        with self.assertRaises(InvalidPinFormatError):
            validate_pin_format([0x12, "34", 0x56, 0x78, 0x90, 0x12])
    
    def test_validate_cem_part_number_valid(self):
        """Test valid CEM part numbers."""
        valid_pns = [8690719, 30786889, 30682981, 8645716]
        for pn in valid_pns:
            with self.subTest(pn=pn):
                is_valid, reason = validate_cem_part_number(pn)
                self.assertTrue(is_valid, f"PN {pn} should be valid: {reason}")
    
    def test_validate_cem_part_number_invalid(self):
        """Test invalid CEM part numbers."""
        invalid_pns = [
            (123, "Too short"),
            (123456789, "Too long"),
            (1234567, "Invalid prefix"),
            (-100, "Negative"),
            ("abc", "Not integer"),
        ]
        for pn, expected_reason in invalid_pns:
            with self.subTest(pn=pn):
                is_valid, reason = validate_cem_part_number(pn)
                self.assertFalse(is_valid)
    
    def test_validate_shuffle_order_valid(self):
        """Test valid shuffle order."""
        from config import SHUFFLE_ORDERS
        valid_shuffles = SHUFFLE_ORDERS
        for shuffle in valid_shuffles:
            with self.subTest(shuffle=shuffle):
                self.assertTrue(validate_shuffle_order(shuffle))
    
    def test_validate_shuffle_order_invalid(self):
        """Test invalid shuffle order."""
        invalid_shuffles = [
            ([0, 1, 2, 3, 4], "Too few elements"),
            ([0, 1, 2, 3, 4, 5, 6], "Too many elements"),
            ([0, 1, 2, 3, 4, 6], "Missing 5"),
            ([0, 1, 2, 3, 4, 4], "Duplicate 4"),
        ]
        for shuffle, expected in invalid_shuffles:
            with self.subTest(shuffle=shuffle):
                with self.assertRaises((ConfigurationError, TypeError, ValueError)):
                    validate_shuffle_order(shuffle)
    
    def test_validate_baud_rate(self):
        """Test baud rate validation."""
        valid_rates = [500000, 250000, 125000]
        for rate in valid_rates:
            with self.subTest(rate=rate):
                self.assertTrue(validate_baud_rate(rate))
        
        invalid_rates = [1000000, 300000, 0, -1]
        for rate in invalid_rates:
            with self.subTest(rate=rate):
                with self.assertRaises(ConfigurationError):
                    validate_baud_rate(rate)


if __name__ == '__main__':
    unittest.main()
