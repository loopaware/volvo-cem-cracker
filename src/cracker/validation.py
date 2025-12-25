"""
Validation functions for Volvo CEM Cracker.

This module provides validation functions for input parameters,
configuration values, and data formats.
"""

from typing import List, Optional, Tuple
from .errors import (
    InvalidPartNumberError,
    InvalidPinFormatError,
    ConfigurationError
)


def validate_pin_format(pin_bytes: List[int], position: int = None) -> bool:
    """
    Validate PIN byte format.
    
    PIN bytes must be valid BCD (Binary Coded Decimal) values:
    - Each byte must be in range 0x00-0x99
    - High nibble represents tens digit (0-9)
    - Low nibble represents units digit (0-9)
    
    Args:
        pin_bytes: List of PIN bytes to validate
        position: Optional specific position to validate
    
    Returns:
        True if valid, raises exception otherwise
    
    Raises:
        InvalidPinFormatError: If PIN format is invalid
    """
    if not isinstance(pin_bytes, (list, tuple)):
        raise InvalidPinFormatError(
            list(pin_bytes) if pin_bytes else [],
            "PIN must be a list or tuple of integers"
        )
    
    if len(pin_bytes) != 6:
        raise InvalidPinFormatError(
            list(pin_bytes),
            f"PIN must be exactly 6 bytes, got {len(pin_bytes)}"
        )
    
    for i, byte in enumerate(pin_bytes):
        if not isinstance(byte, int):
            raise InvalidPinFormatError(
                list(pin_bytes),
                f"Byte at position {i} is not an integer: {type(byte)}"
            )
        
        if byte < 0 or byte > 0x99:
            raise InvalidPinFormatError(
                list(pin_bytes),
                f"Byte at position {i} out of BCD range: {hex(byte)}"
            )
        
        # Check BCD validity (high nibble must be 0-9)
        high_nibble = (byte >> 4) & 0x0F
        if high_nibble > 9:
            raise InvalidPinFormatError(
                list(pin_bytes),
                f"Invalid BCD high nibble at position {i}: {hex(byte)}"
            )
    
    return True


def validate_cem_part_number(pn: int) -> Tuple[bool, Optional[str]]:
    """
    Validate CEM part number format.
    
    Valid part numbers:
    - P1: 7 digits starting with 86/87/31/30
    - P2: 7 or 8 digits starting with 86/94/30/31/94
    
    Args:
        pn: Part number to validate
    
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    if not isinstance(pn, int):
        return False, f"Part number must be an integer, got {type(pn)}"
    
    if pn < 0:
        return False, "Part number cannot be negative"
    
    # Convert to string for pattern matching
    pn_str = str(pn)
    
    # Check length (should be 7-8 digits for Volvo part numbers)
    if len(pn_str) < 7 or len(pn_str) > 8:
        return False, f"Part number should be 7-8 digits, got {len(pn_str)}"
    
    # Check for valid prefixes
    valid_prefixes = ['86', '87', '94', '31', '30', '312']
    if not any(pn_str.startswith(prefix) for prefix in valid_prefixes):
        return False, f"Invalid part number prefix: {pn_str[:2]}"
    
    # Check all characters are digits
    if not pn_str.isdigit():
        return False, "Part number must contain only digits"
    
    return True, None


def validate_shuffle_order(shuffle: List[int]) -> bool:
    """
    Validate shuffle order permutation.
    
    Shuffle order must be a valid permutation of [0, 1, 2, 3, 4, 5].
    
    Args:
        shuffle: Shuffle order to validate
    
    Returns:
        True if valid, raises exception otherwise
    
    Raises:
        ConfigurationError: If shuffle order is invalid
    """
    if not isinstance(shuffle, (list, tuple)):
        raise ConfigurationError(
            "Shuffle order must be a list or tuple",
            "shuffle",
            shuffle
        )
    
    if len(shuffle) != 6:
        raise ConfigurationError(
            f"Shuffle order must have exactly 6 elements, got {len(shuffle)}",
            "shuffle",
            shuffle
        )
    
    # Check for valid permutation
    expected = set(range(6))
    actual = set(shuffle)
    
    if actual != expected:
        missing = expected - actual
        duplicate = actual - expected
        if missing:
            raise ConfigurationError(
                f"Missing elements in shuffle order: {missing}",
                "shuffle",
                shuffle
            )
        if duplicate:
            raise ConfigurationError(
                f"Duplicate elements in shuffle order: {duplicate}",
                "shuffle",
                shuffle
            )
    
    return True


def validate_baud_rate(baud: int) -> bool:
    """
    Validate CAN baud rate.
    
    Common baud rates for Volvo CAN buses:
    - 500000 (500 Kbps) - High speed CAN
    - 250000 (250 Kbps) - Low speed CAN
    - 125000 (125 Kbps) - Very low speed CAN
    
    Args:
        baud: Baud rate to validate
    
    Returns:
        True if valid, raises exception otherwise
    """
    valid_rates = [500000, 250000, 125000]
    
    if baud not in valid_rates:
        raise ConfigurationError(
            f"Invalid baud rate: {baud}. Valid rates: {valid_rates}",
            "baud",
            baud
        )
    
    return True


def validate_samples_count(samples: int, min_samples: int = 1, max_samples: int = 1000) -> bool:
    """
    Validate number of samples for timing attack.
    
    Args:
        samples: Number of samples to validate
        min_samples: Minimum allowed samples
        max_samples: Maximum allowed samples
    
    Returns:
        True if valid, raises exception otherwise
    """
    if not isinstance(samples, int):
        raise ConfigurationError(
            f"Samples count must be an integer, got {type(samples)}",
            "samples",
            samples
        )
    
    if samples < min_samples:
        raise ConfigurationError(
            f"Samples count ({samples}) below minimum ({min_samples})",
            "samples",
            samples
        )
    
    if samples > max_samples:
        raise ConfigurationError(
            f"Samples count ({samples}) above maximum ({max_samples})",
            "samples",
            samples
        )
    
    return True


def validate_start_index(index: int, max_index: int = 1000000) -> bool:
    """
    Validate brute force start index.
    
    Args:
        index: Start index to validate
        max_index: Maximum allowed index (default 1,000,000)
    
    Returns:
        True if valid, raises exception otherwise
    """
    if not isinstance(index, int):
        raise ConfigurationError(
            f"Start index must be an integer, got {type(index)}",
            "start_index",
            index
        )
    
    if index < 0:
        raise ConfigurationError(
            f"Start index cannot be negative: {index}",
            "start_index",
            index
        )
    
    if index >= max_index:
        raise ConfigurationError(
            f"Start index ({index}) exceeds maximum ({max_index})",
            "start_index",
            index
        )
    
    return True
