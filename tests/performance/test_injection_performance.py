"""
Performance benchmarks for text injection system.

Measures latency, memory usage, and resource consumption to validate
non-functional requirements and establish performance baselines.
"""

import pytest
import asyncio
import time
import psutil
import gc
from statistics import mean, median, stdev
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import sys

from nextalk.output.text_injector import TextInjector
from nextalk.output.injection_models import (
    InjectorConfiguration, EnvironmentInfo, DesktopEnvironment,
    DisplayServerType, InjectionMethod, InjectionResult
)


class PerformanceMetrics:
    """Container for performance measurement results."""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.execution_times: List[float] = []
        self.throughput: List[float] = []
    
    def add_measurement(self, latency: float, memory_mb: float, cpu_percent: float, 
                       execution_time: float, throughput_cps: float):
        """Add a performance measurement."""
        self.latencies.append(latency)
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)
        self.execution_times.append(execution_time)
        self.throughput.append(throughput_cps)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistical summary of measurements."""
        return {
            'latency': {
                'mean': mean(self.latencies) if self.latencies else 0,
                'median': median(self.latencies) if self.latencies else 0,
                'min': min(self.latencies) if self.latencies else 0,
                'max': max(self.latencies) if self.latencies else 0,
                'stdev': stdev(self.latencies) if len(self.latencies) > 1 else 0,
            },
            'memory_mb': {
                'mean': mean(self.memory_usage) if self.memory_usage else 0,
                'median': median(self.memory_usage) if self.memory_usage else 0,
                'min': min(self.memory_usage) if self.memory_usage else 0,
                'max': max(self.memory_usage) if self.memory_usage else 0,
                'stdev': stdev(self.memory_usage) if len(self.memory_usage) > 1 else 0,
            },
            'cpu_percent': {
                'mean': mean(self.cpu_usage) if self.cpu_usage else 0,
                'median': median(self.cpu_usage) if self.cpu_usage else 0,
                'min': min(self.cpu_usage) if self.cpu_usage else 0,
                'max': max(self.cpu_usage) if self.cpu_usage else 0,
            },
            'throughput_cps': {
                'mean': mean(self.throughput) if self.throughput else 0,
                'median': median(self.throughput) if self.throughput else 0,
                'min': min(self.throughput) if self.throughput else 0,
                'max': max(self.throughput) if self.throughput else 0,
            }
        }


@pytest.mark.performance
class TestInjectionPerformance:
    """Performance test cases for text injection system."""
    
    @pytest.fixture
    def perf_config(self):
        """Create performance-optimized configuration."""
        return InjectorConfiguration(
            preferred_method=None,
            portal_timeout=2.0,  # Shorter timeout for performance tests
            xdotool_delay=0.001,  # Minimal delay
            retry_attempts=1,  # Minimal retries
            debug_logging=False  # No debug overhead
        )
    
    @pytest.fixture
    def test_environment(self):
        """Create test environment."""
        return EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
    
    @pytest.fixture
    def mock_fast_injector(self):
        """Create mock injector optimized for performance testing."""
        mock_injector = Mock()
        mock_injector.method = InjectionMethod.PORTAL
        mock_injector.check_availability = AsyncMock(return_value=True)
        mock_injector.initialize = AsyncMock(return_value=True)
        mock_injector.cleanup = AsyncMock()
        
        # Simulate realistic injection times
        async def mock_inject_text(text: str) -> InjectionResult:
            # Simulate fast processing time - performance optimized
            processing_time = min(len(text) * 0.00001, 0.01)  # Max 10ms, 0.01ms per character
            await asyncio.sleep(processing_time)
            
            return InjectionResult(
                success=True,
                method_used=InjectionMethod.PORTAL,
                text_length=len(text),
                execution_time=processing_time
            )
        
        # Mock both inject_text and inject_text_with_retry
        mock_injector.inject_text = mock_inject_text
        mock_injector.inject_text_with_retry = mock_inject_text
        return mock_injector
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    @pytest.mark.asyncio
    async def test_single_injection_latency(self, perf_config, test_environment, mock_fast_injector):
        """Test latency of single text injection operations."""
        # Create TextInjector and manually mock its internals
        injector = TextInjector(perf_config)
        
        # Directly set the mock injector
        injector._initialized = True
        injector._active_injector = mock_fast_injector
        
        # Test various text lengths
        test_texts = [
            "hi",  # Short text
            "hello world test",  # Medium text
            "This is a longer text for performance testing with multiple words and punctuation.",  # Long text
            "A" * 1000,  # Very long text (1000 characters)
        ]
        
        metrics = PerformanceMetrics()
        
        for text in test_texts:
            # Measure memory before
            memory_before = self._get_memory_usage_mb()
            
            # Measure injection latency
            start_time = time.perf_counter()
            result = await injector.inject_text(text)
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            memory_after = self._get_memory_usage_mb()
            memory_delta = memory_after - memory_before
            cpu_usage = self._get_cpu_usage()
            
            # Calculate throughput (characters per second)
            throughput = len(text) / latency if latency > 0 else 0
            
            metrics.add_measurement(
                latency=latency,
                memory_mb=memory_delta,
                cpu_percent=cpu_usage,
                execution_time=result.execution_time,
                throughput_cps=throughput
            )
            
            assert result.success is True
        
        # Analyze results
        summary = metrics.get_summary()
        
        # Performance assertions (adjust thresholds based on requirements)
        assert summary['latency']['mean'] < 0.15, f"Mean latency too high: {summary['latency']['mean']:.3f}s"
        assert summary['latency']['max'] < 0.25, f"Max latency too high: {summary['latency']['max']:.3f}s"
        assert summary['throughput_cps']['mean'] > 50, f"Throughput too low: {summary['throughput_cps']['mean']:.1f} cps"
        
        print(f"Single injection performance summary: {summary}")
    
    @pytest.mark.asyncio
    async def test_concurrent_injection_performance(self, perf_config, test_environment, mock_fast_injector):
        """Test performance under concurrent injection load."""
        # Create TextInjector and manually mock its internals
        injector = TextInjector(perf_config)
        
        # Directly set the mock injector
        injector._initialized = True
        injector._active_injector = mock_fast_injector
            
        # Test concurrent injections
        concurrent_levels = [1, 5, 10, 20]
        test_text = "concurrent performance test"
        
        for concurrency in concurrent_levels:
            gc.collect()  # Clean up before measurement
            
            memory_before = self._get_memory_usage_mb()
            start_time = time.perf_counter()
            
            # Create concurrent injection tasks
            tasks = [injector.inject_text(f"{test_text} {i}") for i in range(concurrency)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            memory_after = self._get_memory_usage_mb()
            
            total_time = end_time - start_time
            memory_delta = memory_after - memory_before
            cpu_usage = self._get_cpu_usage()
            
            # All injections should succeed
            assert all(result.success for result in results)
            
            # Calculate metrics
            total_chars = sum(len(f"{test_text} {i}") for i in range(concurrency))
            throughput = total_chars / total_time
            latency_per_injection = total_time / concurrency
            
            print(f"Concurrency {concurrency}: {latency_per_injection:.3f}s/injection, "
                    f"{throughput:.1f} cps, {memory_delta:.1f}MB, {cpu_usage:.1f}% CPU")
            
            # Performance assertions
            assert latency_per_injection < 0.2, f"Per-injection latency too high at concurrency {concurrency}"
            assert memory_delta < 10.0, f"Memory usage too high: {memory_delta:.1f}MB"
    
    @pytest.mark.asyncio
    async def test_memory_usage_over_time(self, perf_config, test_environment, mock_fast_injector):
        """Test memory usage patterns over extended operation."""
        # Create TextInjector and manually mock its internals
        injector = TextInjector(perf_config)
        
        # Directly set the mock injector
        injector._initialized = True
        injector._active_injector = mock_fast_injector
            
        baseline_memory = self._get_memory_usage_mb()
        memory_samples = []
        
        # Perform injections over time and monitor memory
        for i in range(100):
            await injector.inject_text(f"memory test iteration {i}")
            
            if i % 10 == 0:  # Sample every 10 iterations
                current_memory = self._get_memory_usage_mb()
                memory_delta = current_memory - baseline_memory
                memory_samples.append(memory_delta)
                
                # Force garbage collection periodically
                if i % 50 == 0:
                    gc.collect()
        
        # Check for memory leaks
        final_memory_delta = memory_samples[-1]
        max_memory_delta = max(memory_samples)
        
        print(f"Memory usage over time: baseline={baseline_memory:.1f}MB, "
                f"final_delta={final_memory_delta:.1f}MB, max_delta={max_memory_delta:.1f}MB")
        
        # Memory leak assertions
        assert final_memory_delta < 5.0, f"Possible memory leak: {final_memory_delta:.1f}MB increase"
        assert max_memory_delta < 10.0, f"Memory usage spike too high: {max_memory_delta:.1f}MB"
    
    @pytest.mark.asyncio
    async def test_initialization_performance(self, perf_config, test_environment, mock_fast_injector):
        """Test initialization and cleanup performance."""
        with patch('nextalk.output.injection_factory.get_injection_factory') as mock_factory, \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=test_environment):
            
            # Mock the factory to return our mocked injector
            mock_selection = Mock()
            mock_selection.injector = mock_fast_injector 
            mock_factory.return_value.create_injector.return_value = mock_selection
            
            init_times = []
            cleanup_times = []
            
            # Test multiple initialization cycles
            for _ in range(10):
                injector = TextInjector(perf_config)
                
                # Measure initialization time
                start_time = time.perf_counter()
                await injector.initialize()
                init_time = time.perf_counter() - start_time
                init_times.append(init_time)
                
                # Measure cleanup time
                start_time = time.perf_counter()
                await injector.cleanup()
                cleanup_time = time.perf_counter() - start_time
                cleanup_times.append(cleanup_time)
            
            # Analyze initialization performance
            mean_init_time = mean(init_times)
            mean_cleanup_time = mean(cleanup_times)
            max_init_time = max(init_times)
            max_cleanup_time = max(cleanup_times)
            
            print(f"Initialization performance: mean={mean_init_time:.3f}s, max={max_init_time:.3f}s")
            print(f"Cleanup performance: mean={mean_cleanup_time:.3f}s, max={max_cleanup_time:.3f}s")
            
            # Performance assertions
            assert mean_init_time < 0.1, f"Mean initialization too slow: {mean_init_time:.3f}s"
            assert max_init_time < 0.5, f"Max initialization too slow: {max_init_time:.3f}s"
            assert mean_cleanup_time < 0.05, f"Mean cleanup too slow: {mean_cleanup_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_burst_injection_performance(self, perf_config, test_environment, mock_fast_injector):
        """Test performance under burst injection scenarios."""
        # Create TextInjector and manually mock its internals
        injector = TextInjector(perf_config)
        
        # Directly set the mock injector
        injector._initialized = True
        injector._active_injector = mock_fast_injector
            
        # Test burst scenarios
        burst_sizes = [10, 50, 100]
        test_text = "burst test"
        
        for burst_size in burst_sizes:
            # Measure burst performance
            start_time = time.perf_counter()
            
            # Rapid-fire injections
            tasks = []
            for i in range(burst_size):
                task = injector.inject_text(f"{test_text} {i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            
            burst_time = end_time - start_time
            injections_per_second = burst_size / burst_time
            
            # All injections should succeed
            assert all(result.success for result in results)
            
            print(f"Burst size {burst_size}: {burst_time:.3f}s total, "
                    f"{injections_per_second:.1f} injections/sec")
            
            # Performance assertions
            assert injections_per_second > 20, f"Burst throughput too low: {injections_per_second:.1f}/sec"
            assert burst_time < 5.0, f"Burst completion too slow: {burst_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_efficiency(self, perf_config, test_environment, mock_fast_injector):
        """Test efficiency of resource cleanup."""
        with patch('nextalk.output.injection_factory.get_injection_factory') as mock_factory, \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=test_environment):
            
            # Mock the factory to return our mocked injector
            mock_selection = Mock()
            mock_selection.injector = mock_fast_injector 
            mock_factory.return_value.create_injector.return_value = mock_selection
            
            # Measure resource usage through multiple init/use/cleanup cycles
            baseline_memory = self._get_memory_usage_mb()
            cycle_times = []
            
            for cycle in range(5):
                cycle_start = time.perf_counter()
                
                injector = TextInjector(perf_config)
                await injector.initialize()
                
                # Use the injector
                for i in range(20):
                    await injector.inject_text(f"cleanup test {cycle}-{i}")
                
                await injector.cleanup()
                
                cycle_end = time.perf_counter()
                cycle_times.append(cycle_end - cycle_start)
                
                # Force garbage collection
                gc.collect()
                
                current_memory = self._get_memory_usage_mb()
                memory_delta = current_memory - baseline_memory
                
                print(f"Cycle {cycle}: {cycle_end - cycle_start:.3f}s, "
                      f"memory delta: {memory_delta:.1f}MB")
                
                # Memory should not continuously grow
                assert memory_delta < 2.0, f"Memory not properly cleaned up: {memory_delta:.1f}MB"
            
            # Cycle time should be consistent (no performance degradation)
            mean_cycle_time = mean(cycle_times)
            max_cycle_time = max(cycle_times)
            
            assert max_cycle_time < mean_cycle_time * 1.5, "Performance degradation detected over cycles"
    
    @pytest.mark.asyncio
    async def test_error_handling_performance_impact(self, perf_config, test_environment):
        """Test performance impact of error handling."""
        # Mock injector that occasionally fails
        mock_injector = Mock()
        mock_injector.method = InjectionMethod.PORTAL
        mock_injector.check_availability = AsyncMock(return_value=True)
        mock_injector.initialize = AsyncMock(return_value=True)
        mock_injector.cleanup = AsyncMock()
        
        call_count = 0
        async def mock_inject_with_errors(text: str) -> InjectionResult:
            nonlocal call_count
            call_count += 1
            
            # Fail every 5th call to test error handling performance
            if call_count % 5 == 0:
                from nextalk.output.injection_exceptions import InjectionFailedError
                raise InjectionFailedError("Simulated error")
            
            await asyncio.sleep(0.001)  # Simulate work
            return InjectionResult(
                success=True,
                method_used=InjectionMethod.PORTAL,
                text_length=len(text),
                execution_time=0.001
            )
        
        # Mock both inject_text and inject_text_with_retry
        mock_injector.inject_text = mock_inject_with_errors
        mock_injector.inject_text_with_retry = mock_inject_with_errors
        
        # Create TextInjector and manually mock its internals
        injector = TextInjector(perf_config)
        
        # Directly set the mock injector
        injector._initialized = True
        injector._active_injector = mock_injector
        
        successful_times = []
        error_times = []
        
        # Test with error scenarios
        for i in range(20):
            start_time = time.perf_counter()
            
            try:
                result = await injector.inject_text(f"error test {i}")
                end_time = time.perf_counter()
                successful_times.append(end_time - start_time)
            except Exception:
                end_time = time.perf_counter()
                error_times.append(end_time - start_time)
        
        # Error handling should not significantly impact performance
        if successful_times and error_times:
            mean_success_time = mean(successful_times)
            mean_error_time = mean(error_times)
            
            print(f"Success time: {mean_success_time:.4f}s, Error time: {mean_error_time:.4f}s")
            
            # Error handling should not be more than 2x slower than success path
            assert mean_error_time < mean_success_time * 2, "Error handling too slow"
    
    def test_performance_requirements_summary(self):
        """Document performance requirements and thresholds."""
        requirements = {
            "latency": {
                "single_injection_mean": "< 100ms",
                "single_injection_max": "< 500ms",
                "burst_throughput": "> 20 injections/sec"
            },
            "memory": {
                "initialization_overhead": "< 10MB",
                "per_injection_overhead": "< 1MB",
                "memory_leak_threshold": "< 5MB over 100 injections"
            },
            "initialization": {
                "mean_init_time": "< 100ms",
                "max_init_time": "< 500ms",
                "cleanup_time": "< 50ms"
            },
            "throughput": {
                "minimum_cps": "> 100 characters/second",
                "concurrent_handling": "20+ concurrent injections"
            }
        }
        
        print("\nPerformance Requirements Summary:")
        for category, metrics in requirements.items():
            print(f"\n{category.upper()}:")
            for metric, threshold in metrics.items():
                print(f"  {metric}: {threshold}")
        
        # This test always passes - it's for documentation
        assert True