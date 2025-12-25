import logging
import logging.handlers
import sys
import os
from .config import LOG_FILE

def setup_logging():
    log_path = LOG_FILE
    is_prod = log_path.startswith('/var/log')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Use rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        log_path, 
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also log to console for dev environments
    if not is_prod:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logging.info("Logging initialized.")

def bcd_to_bin(val):
    return ((val >> 4) * 10) + (val & 0x0F)

def bin_to_bcd(val):
    # Use lookup if in range, else calc
    if 0 <= val < 100:
        return BCD_TABLE[val]
    return ((val // 10) << 4) | (val % 10)
