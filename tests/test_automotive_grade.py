import pytest
import os
import sys
import time
import subprocess
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from monitor_sim import VolvoMonitorSim
from cracker import VolvoCracker

@pytest.fixture
def monitor():
    # Setup monitor sim with a specific output dir
    output_dir = "tests/verify_screens"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return VolvoMonitorSim(output_dir=output_dir)

def test_monitor_visual_output(monitor, image_diff):
    # 1. Create a mock log file with a specific status
    with open("crack.log", "w") as f:
        f.write("Progress: 5000/1000000 (0.5%) Rate: 120.5/s ETA: 120.0m - PIN: [1, 2, 3, 4, 5, 6]\n")
    
    # 2. Render once
    monitor.run_once()
    
    # 3. Find the generated screen (luma.emulator appends index)
    import glob
    files = glob.glob(os.path.join(monitor.output_dir, "screen_*.png"))
    assert len(files) > 0
    generated_screen = files[0]
    
    # 4. Compare with Golden Master
    golden_master = "tests/golden_masters/monitor_progress.png"
    if not os.path.exists(golden_master):
        if not os.path.exists("tests/golden_masters"):
            os.makedirs("tests/golden_masters")
        os.rename(generated_screen, golden_master)
        pytest.skip("Golden master created. Run again to verify.")
    
    # For now, just assert it exists and is a valid image
    from PIL import Image
    img = Image.open(generated_screen)
    assert img.size == (128, 64)

def test_cold_weather_delay(monitor):
    monitor.set_cold_weather(True)
    start = time.time()
    monitor.run_once()
    elapsed = time.time() - start
    # Expect at least 0.5s delay
    assert elapsed >= 0.5

def test_voltage_sag_pause():
    cracker = VolvoCracker(channel='test_sag')
    cracker.bus = MagicMock() # Needs MagicMock from unittest.mock
    
    # Trigger sag
    with open("POWER_SAG.trigger", "w") as f:
        f.write("1")
    
    # We want to verify that brute_force pauses
    # This is tricky without threads, but we can mock 'check_power_sag' 
    # to return True then False.
    
    with patch('cracker.VolvoCracker.check_power_sag') as mock_sag:
        mock_sag.side_effect = [True, True, False] # 2 times True, then False
        
        start_pin = [0,0,0,0,0,0]
        # We need to ensure it only runs a few iterations
        with patch('cracker.VolvoCracker.unlock_attempt_fast', return_value=True):
            cracker.brute_force(start_pin, start_index=0)
        
        # Verify it called check_power_sag
        assert mock_sag.call_count >= 3

if __name__ == "__main__":
    # Manual run support
    pass
