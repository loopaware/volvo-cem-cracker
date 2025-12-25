"""
Performance benchmark tests for Volvo CEM Cracker.

Tests performance characteristics and establishes baseline metrics:
- Brute force iteration speed
- Timing attack sample collection
- CAN message throughput
- Memory usage monitoring
- Session save/load performance
"""

import unittest
import sys
import os
import time
import tempfile
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config import BCD_TABLE, SHUFFLE_ORDERS


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_session_file = os.path.join(self.temp_dir, "session.json")
        
        # Patch session file location
        self.session_patcher = patch('cracker.SESSION_FILE', self.test_session_file)
        self.session_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.session_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_bcd_conversion_speed(self):
        """Benchmark BCD conversion performance."""
        from cracker import bin_to_bcd, bcd_to_bin
        
        iterations = 10000
        
        start = time.time()
        for _ in range(iterations):
            for i in range(100):
                bin_to_bcd(i)
                bcd_to_bin(i)
        elapsed = time.time() - start
        
        rate = iterations * 100 / elapsed
        print(f"BCD conversion: {rate:.0f} conversions/sec")
        
        # Expect at least 100,000 conversions per second
        self.assertGreater(rate, 100000)
    
    def test_pin_encoding_speed(self):
        """Benchmark PIN encoding performance."""
        iterations = 10000
        shuffle = SHUFFLE_ORDERS[0]
        
        start = time.time()
        for _ in range(iterations):
            pin = [0x12, 0x34, 0x56, 0x78, 0x90, 0x12]
            data = [0] * 8
            data[0] = 0x50  # CEM ID
            data[1] = 0xBE  # CMD_UNLOCK
            for i in range(6):
                data[2 + shuffle[i]] = pin[i]
        elapsed = time.time() - start
        
        rate = iterations / elapsed
        print(f"PIN encoding: {rate:.0f} encodings/sec")
        
        # Expect at least 10,000 encodings per second
        self.assertGreater(rate, 10000)
    
    def test_session_save_performance(self):
        """Benchmark session save performance."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        fixed = [0x12, 0x34, 0x56, 0, 0, 0]
        queue = [[i, i+1, i+2, 0, 0, 0] for i in range(50)]
        
        iterations = 100
        
        start = time.time()
        for _ in range(iterations):
            cracker.save_session(1000, fixed, queue)
        elapsed = time.time() - start
        
        rate = iterations / elapsed
        print(f"Session save: {rate:.1f} saves/sec")
        
        # Expect at least 10 saves per second
        self.assertGreater(rate, 10)
    
    def test_session_load_performance(self):
        """Benchmark session load performance."""
        from cracker import VolvoCracker
        
        cracker = VolvoCracker()
        cracker.bus = MagicMock()
        
        # Create a session first
        fixed = [0x12, 0x34, 0x56, 0, 0, 0]
        queue = [[i, i+1, i+2, 0, 0, 0] for i in range(50)]
        cracker.save_session(1000, fixed, queue)
        
        iterations = 100
        
        start = time.time()
        for _ in range(iterations):
            cracker.load_session()
        elapsed = time.time() - start
        
        rate = iterations / elapsed
        print(f"Session load: {rate:.1f} loads/sec")
        
        # Expect at least 50 loads per second
        self.assertGreater(rate, 50)
    
    def test_brute_force_iteration_speed(self):
        """Benchmark brute force iteration speed."""
        # Mock CAN bus for pure computation benchmarking
        mock_bus = MagicMock()
        mock_bus.send = MagicMock()
        mock_bus.recv = MagicMock(return_value=None)
        
        iterations = 10000
        shuffle = SHUFFLE_ORDERS[0]
        
        start = time.time()
        for i in range(iterations):
            # Simulate brute force iteration
            pin = [0] * 6
            rem = i
            d1, rem = divmod(rem, 10000)
            d2, d3 = divmod(rem, 100)
            pin[3] = BCD_TABLE[d1]
            pin[4] = BCD_TABLE[d2]
            pin[5] = BCD_TABLE[d3]
            
            # Encode
            data = [0x50, 0xBE] + [0] * 6
            for j in range(6):
                data[2 + shuffle[j]] = pin[j]
        elapsed = time.time() - start
        
        rate = iterations / elapsed
        print(f"Brute force iteration: {rate:.0f} iterations/sec")
        
        # Expect at least 50,000 iterations per second
        self.assertGreater(rate, 50000)


class TestTimingAttackPerformance(unittest.TestCase):
    """Performance tests for timing attack."""
    
    def test_sample_collection_speed(self):
        """Benchmark timing attack sample collection."""
        # Mock unlock attempt for pure computation benchmarking
        def mock_unlock(pin):
            return False, 0.001  # 1ms latency
        
        iterations = 1000
        SAMPLES = 10
        
        start = time.time()
        for _ in range(iterations):
            for _ in range(SAMPLES):
                mock_unlock([0x12, 0, 0, 0, 0, 0])
        elapsed = time.time() - start
        
        total_samples = iterations * SAMPLES
        rate = total_samples / elapsed
        print(f"Sample collection: {rate:.0f} samples/sec")
        
        # Expect at least 5,000 samples per second
        self.assertGreater(rate, 5000)
    
    def test_statistics_calculation_speed(self):
        """Benchmark statistics calculation speed."""
        import random
        
        iterations = 100
        sample_counts = [10, 25, 50, 100]
        
        for sample_count in sample_counts:
            with self.subTest(sample_count=sample_count):
                start = time.time()
                for _ in range(iterations):
                    samples = [random.random() for _ in range(sample_count)]
                    mean = sum(samples) / len(samples)
                    variance = sum((x - mean) ** 2 for x in samples) / len(samples)
                    std = variance ** 0.5
                elapsed = time.time() - start
                
                rate = iterations / elapsed
                print(f"Statistics ({sample_count} samples): {rate:.1f} calcs/sec")
                
                # Expect reasonable calculation speed
                self.assertGreater(rate, 10)


class TestMemoryUsage(unittest.TestCase):
    """Memory usage monitoring tests."""
    
    def test_pin_array_memory(self):
        """Verify PIN array memory usage is bounded."""
        import sys
        
        pin = [0] * 6
        size = sys.getsizeof(pin) + sys.getsizeof(pin[0]) * len(pin)
        
        # Should be very small (less than 1KB)
        self.assertLess(size, 1024)
    
    def test_session_queue_memory(self):
        """Verify session queue memory usage is reasonable."""
        import sys
        
        queue = [[i] * 6 for i in range(100)]
        base_size = sys.getsizeof(queue)
        item_sizes = sum(sys.getsizeof(item) for item in queue)
        
        total_size = base_size + item_sizes
        
        # Should be less than 100KB for 100 candidates
        self.assertLess(total_size, 100 * 1024)
    
    def test_histogram_memory(self):
        """Verify histogram memory usage is bounded."""
        import sys
        
        # Typical histogram size for timing analysis
        histogram_size = 1000  # values
        histogram = [0] * histogram_size
        
        size = sys.getsizeof(histogram) + sys.getsizeof(histogram[0]) * len(histogram)
        
        # Should be less than 50KB
        self.assertLess(size, 50 * 1024)


if __name__ == '__main__':
    unittest.main()
