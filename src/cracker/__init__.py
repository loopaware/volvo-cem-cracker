"""
Volvo CEM Cracker Package

This package provides comprehensive tools for cracking Volvo Central Electronic Module (CEM)
PIN codes using timing attacks and brute force methods over the CAN bus.
"""

# Re-export key components from config (use absolute import)
from src.config import (
    REQ_ID, CEM_HS_ID, CEM_LS_ID, CMD_UNLOCK, CMD_UNLOCK_REPLY,
    SHUFFLE_ORDERS, CEM_PARAMS, BCD_TABLE, SESSION_FILE, LOG_FILE
)

# Re-export utility functions (use absolute import)
from src.utils import bcd_to_bin, bin_to_bcd

# Re-export exception classes (these use only standard library imports, so they're safe)
from src.cracker.errors import (
    CrackerError, CanBusError, SessionError, ConfigurationError,
    InvalidPartNumberError, InvalidPinFormatError
)

# Re-export validation functions (these use only standard library imports)
from src.cracker.validation import (
    validate_pin_format, validate_cem_part_number, 
    validate_shuffle_order, validate_baud_rate
)

# Re-export session manager (uses only standard library imports)
from src.cracker.session import SessionManager

# Re-export core functions (internal relative imports are okay here)
from src.cracker.unlock import unlock_attempt_fast, unlock_attempt_timing
from src.cracker.timing_attack import crack_timing  
from src.cracker.brute_force import brute_force

# Set VolvoCracker as an alias
VolvoCracker = None
try:
    from src.cracker.cem_cracker import CemCracker
    VolvoCracker = CemCracker
except ImportError:
    pass

__all__ = [
    'SessionManager',
    'VolvoCracker',
    'unlock_attempt_fast',
    'unlock_attempt_timing', 
    'crack_timing',
    'brute_force',
    'bcd_to_bin',
    'bin_to_bcd',
    'REQ_ID',
    'CEM_HS_ID', 
    'CEM_LS_ID',
    'CMD_UNLOCK',
    'CMD_UNLOCK_REPLY',
    'SHUFFLE_ORDERS',
    'CEM_PARAMS',
    'BCD_TABLE',
    'SESSION_FILE',
    'LOG_FILE',
    'CrackerError',
    'CanBusError',
    'SessionError', 
    'ConfigurationError',
    'InvalidPartNumberError',
    'InvalidPinFormatError',
    'validate_pin_format',
    'validate_cem_part_number',
    'validate_shuffle_order',
    'validate_baud_rate',
]
