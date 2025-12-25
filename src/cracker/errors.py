"""
Custom exception classes for Volvo CEM Cracker.

This module defines a hierarchy of exceptions for robust error handling
and clear error reporting throughout the application.
"""

import time


class CrackerError(Exception):
    """Base exception for all cracker-related errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"
    
    def to_dict(self):
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class CanBusError(CrackerError):
    """Exception raised for CAN bus related errors."""
    
    def __init__(self, message: str, bus_id: str = None, error_code: int = None):
        details = {}
        if bus_id:
            details["bus_id"] = bus_id
        if error_code is not None:
            details["error_code"] = error_code
        super().__init__(message, details)


class CanInitializationError(CanBusError):
    """Exception raised when CAN bus initialization fails."""
    
    def __init__(self, bus_id: str, reason: str):
        super().__init__(
            f"Failed to initialize CAN bus {bus_id}: {reason}",
            bus_id=bus_id
        )


class CanCommunicationError(CanBusError):
    """Exception raised when CAN communication fails."""
    
    def __init__(self, bus_id: str, operation: str, timeout: float = None):
        details = {"operation": operation}
        if timeout:
            details["timeout"] = timeout
        super().__init__(
            f"CAN communication error on {bus_id} during {operation}",
            bus_id=bus_id,
            error_code=None
        )


class SessionError(CrackerError):
    """Exception raised for session management errors."""
    
    def __init__(self, message: str, session_file: str = None):
        details = {}
        if session_file:
            details["session_file"] = session_file
        super().__init__(message, details)


class SessionCorruptionError(SessionError):
    """Exception raised when session file is corrupted."""
    
    def __init__(self, session_file: str, corruption_details: str):
        super().__init__(
            f"Session file corruption detected: {corruption_details}",
            session_file=session_file
        )
        self.corruption_details = corruption_details


class SessionSaveError(SessionError):
    """Exception raised when session cannot be saved."""
    
    def __init__(self, session_file: str, reason: str):
        super().__init__(
            f"Failed to save session to {session_file}: {reason}",
            session_file=session_file
        )


class ConfigurationError(CrackerError):
    """Exception raised for configuration validation errors."""
    
    def __init__(self, message: str, config_param: str = None, invalid_value = None):
        details = {}
        if config_param:
            details["config_param"] = config_param
        if invalid_value is not None:
            details["invalid_value"] = invalid_value
        super().__init__(message, details)


class InvalidPartNumberError(ConfigurationError):
    """Exception raised when CEM part number is invalid."""
    
    def __init__(self, part_number: int, reason: str = None):
        details = {"part_number": part_number}
        message = f"Invalid CEM part number: {part_number}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, details.get("config_param", "part_number"), part_number)
        self.details = details


class InvalidPinFormatError(ConfigurationError):
    """Exception raised when PIN format is invalid."""
    
    def __init__(self, pin_bytes: list, reason: str = None):
        details = {"pin_bytes": pin_bytes, "length": len(pin_bytes)}
        message = f"Invalid PIN format: {pin_bytes}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, details.get("config_param", "pin_format"), pin_bytes)
        self.details = details


class TimeoutError(CrackerError):
    """Exception raised when an operation times out."""
    
    def __init__(self, operation: str, timeout_duration: float, elapsed: float):
        super().__init__(
            f"Operation '{operation}' timed out after {elapsed:.2f}s (timeout: {timeout_duration}s)",
            details={
                "operation": operation,
                "timeout_duration": timeout_duration,
                "elapsed": elapsed
            }
        )
