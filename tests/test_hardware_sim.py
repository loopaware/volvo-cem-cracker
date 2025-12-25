import pytest
import can
import time
import subprocess
import os
import signal
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cracker import VolvoCracker, bcd_to_bin

# Setup vcan0 if it doesn't exist (requires sudo, but we assume it's there or user handled it)
@pytest.fixture(scope="session", autouse=True)
def vcan_setup():
    # Attempt to create vcan0 if it doesn't exist
    # This might fail in non-privileged env, so we just log and continue
    try:
        subprocess.run(["sudo", "ip", "link", "add", "dev", "vcan0", "type", "vcan"], capture_output=True)
        subprocess.run(["sudo", "ip", "link", "set", "up", "vcan0"], capture_output=True)
    except:
        pass
    yield

@pytest.fixture
def cem_simulator():
    """Starts the CEM simulator on vcan0."""
    secret_pin = [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]
    # Run sim_cem.py as a subprocess using the current interpreter
    # Use absolute path to avoid directory issues
    sim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/sim_cem.py'))
    proc = subprocess.Popen([
        sys.executable, sim_path, 
        "--channel", "vcan0", 
        "--pin", "123456789012"
    ])
    time.sleep(1) # Wait for it to start
    yield secret_pin
    proc.terminate()
    proc.wait()

def test_timing_attack_reliability(cem_simulator):
    """Verifies that the timing attack can distinguish matching prefixes."""
    cracker = VolvoCracker(channel='vcan0')
    cracker.setup_can(500000)
    
    secret_pin = cem_simulator
    
    # Analyze position 0
    # We expect the secret_pin[0] (0x12) to have higher latency than others
    stats = {}
    SAMPLES = 10
    
    test_values = [0x00, 0x12, 0x55, 0x99] # Include the real one and some others
    
    for val in test_values:
        total_lat = 0
        for _ in range(SAMPLES):
            pin = [val, 0, 0, 0, 0, 0]
            suc, lat = cracker.unlock_attempt_timing(pin)
            total_lat += lat
        stats[val] = total_lat / SAMPLES
        print(f"Val: {hex(val)}, Latency: {stats[val]*1000:.2f}ms")
    
    # The real value (0x12) should be the maximum
    max_val = max(stats, key=stats.get)
    assert max_val == 0x12, f"Expected 0x12 to be slowest, but got {hex(max_val)}"

def test_full_crack_against_sim(cem_simulator):
    """Verifies the cracker can find the PIN against the real simulator over vcan."""
    cracker = VolvoCracker(channel='vcan0')
    cracker.setup_can(500000)
    
    # Shorten the brute force by starting close
    # PIN: [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]
    # Index for 789012
    start_pin = [0x12, 0x34, 0x56, 0, 0, 0]
    found = cracker.brute_force(start_pin, start_index=789010)
    
    assert found == [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]
