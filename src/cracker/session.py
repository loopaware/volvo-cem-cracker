"""
Enhanced session management with robust error handling.

This module provides atomic session save/load operations with
corruption detection and recovery capabilities.
"""

import json
import os
import time
import logging
from typing import Tuple, List, Optional
from .errors import (
    SessionError,
    SessionCorruptionError,
    SessionSaveError
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages cracking session state with robust error handling.
    
    Features:
    - Atomic file operations (using temp files)
    - Corruption detection and recovery
    - Backup session files
    - Validation of loaded session data
    """
    
    def __init__(self, session_file: str, backup_file: str = None):
        """
        Initialize session manager.
        
        Args:
            session_file: Path to session file
            backup_file: Path to backup session file (optional)
        """
        self.session_file = session_file
        self.backup_file = backup_file or session_file + ".bak"
        self.temp_file = session_file + ".tmp"
    
    def save_session(self, index: int, fixed_bytes: List[int], 
                    candidates_queue: List[List[int]]) -> bool:
        """
        Atomically save session state.
        
        Uses temp file and atomic replace to prevent corruption
        during save operations.
        
        Args:
            index: Current brute force index
            fixed_bytes: Fixed PIN bytes
            candidates_queue: Queue of candidate PIN prefixes
        
        Returns:
            True if save successful, raises exception otherwise
        """
        # Validate input
        self._validate_session_data(index, fixed_bytes, candidates_queue)
        
        # Prepare session data
        state = {
            "version": "1.0",
            "timestamp": time.time(),
            "index": index,
            "fixed_bytes": fixed_bytes,
            "candidates_queue": candidates_queue
        }
        
        try:
            # Write to temp file first
            with open(self.temp_file, "w") as f:
                json.dump(state, f, indent=2)
            
            # Atomic replace
            os.replace(self.temp_file, self.session_file)
            
            # Update backup
            self._update_backup()
            
            logger.debug(f"Session saved: index={index}, fixed={fixed_bytes[:3]}...")
            return True
            
        except PermissionError as e:
            raise SessionSaveError(
                self.session_file,
                f"Permission denied: {e}"
            )
        except OSError as e:
            raise SessionSaveError(
                self.session_file,
                f"OS error: {e}"
            )
        except Exception as e:
            raise SessionSaveError(
                self.session_file,
                f"Unexpected error: {e}"
            )
    
    def load_session(self) -> Tuple[Optional[int], Optional[List[int]], List[List[int]]]:
        """
        Load session state with corruption detection.
        
        Returns:
            Tuple of (index, fixed_bytes, candidates_queue)
            Returns (None, None, []) if no valid session found
        
        Raises:
            SessionCorruptionError: If session file is corrupted
        """
        # Try primary session file first
        if os.path.exists(self.session_file):
            try:
                return self._load_and_validate(self.session_file)
            except SessionCorruptionError:
                logger.warning("Primary session file corrupted, trying backup...")
        
        # Try backup file
        if os.path.exists(self.backup_file):
            try:
                return self._load_and_validate(self.backup_file)
            except SessionCorruptionError:
                logger.warning("Backup session file also corrupted")
        
        # No valid session found
        logger.info("No valid session found, starting fresh")
        return None, None, []
    
    def _load_and_validate(self, filepath: str) -> Tuple[int, List[int], List[List[int]]]:
        """
        Load and validate session file.
        
        Args:
            filepath: Path to session file
        
        Returns:
            Tuple of (index, fixed_bytes, candidates_queue)
        
        Raises:
            SessionCorruptionError: If file is corrupted or invalid
        """
        try:
            with open(filepath, "r") as f:
                state = json.load(f)
        except json.JSONDecodeError as e:
            raise SessionCorruptionError(
                filepath,
                f"Invalid JSON: {e}"
            )
        
        # Validate required fields
        required_fields = ["version", "timestamp", "index", "fixed_bytes", "candidates_queue"]
        for field in required_fields:
            if field not in state:
                raise SessionCorruptionError(
                    filepath,
                    f"Missing required field: {field}"
                )
        
        # Validate field types
        if not isinstance(state["index"], int):
            raise SessionCorruptionError(
                filepath,
                f"Index must be integer, got {type(state['index'])}"
            )
        
        if not isinstance(state["fixed_bytes"], (list, tuple)):
            raise SessionCorruptionError(
                filepath,
                f"Fixed bytes must be list, got {type(state['fixed_bytes'])}"
            )
        
        if len(state["fixed_bytes"]) != 6:
            raise SessionCorruptionError(
                filepath,
                f"Fixed bytes must be 6 elements, got {len(state['fixed_bytes'])}"
            )
        
        if not isinstance(state["candidates_queue"], list):
            raise SessionCorruptionError(
                filepath,
                f"Candidates queue must be list, got {type(state['candidates_queue'])}"
            )
        
        # Apply rewind logic (start 500 positions before saved index)
        index = max(0, state["index"] - 500)
        
        logger.debug(f"Session loaded: index={index}, fixed={state['fixed_bytes'][:3]}...")
        return index, state["fixed_bytes"], state["candidates_queue"]
    
    def _update_backup(self):
        """Update backup file with current session state."""
        try:
            if os.path.exists(self.session_file):
                os.replace(self.session_file, self.backup_file)
        except OSError:
            # Backup update failed, but that's okay
            logger.warning("Failed to update backup file")
    
    def _validate_session_data(self, index: int, fixed_bytes: List[int], 
                              candidates_queue: List[List[int]]):
        """Validate session data before saving."""
        if index < 0:
            raise SessionError("Session index cannot be negative", self.session_file)
        
        if len(fixed_bytes) != 6:
            raise SessionError(
                f"Fixed bytes must be 6 elements, got {len(fixed_bytes)}",
                self.session_file
            )
        
        if not isinstance(candidates_queue, list):
            raise SessionError(
                "Candidates queue must be a list",
                self.session_file
            )
    
    def clear_session(self) -> bool:
        """
        Clear all session files.
        
        Returns:
            True if successful
        """
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
            return True
        except OSError as e:
            logger.warning(f"Failed to clear session files: {e}")
            return False
