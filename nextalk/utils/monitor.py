"""
Performance monitoring utilities for NexTalk.

Provides performance tracking and system monitoring.
"""

import time
import threading
import psutil
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import statistics


logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Represents a single metric measurement."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Performance statistics."""
    operation: str
    count: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    p95_time: float
    p99_time: float


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, monitor: Optional['PerformanceMonitor'] = None):
        """
        Initialize timer.
        
        Args:
            name: Operation name
            monitor: Optional monitor to report to
        """
        self.name = name
        self.monitor = monitor
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        
        if self.monitor:
            self.monitor.record_timing(self.name, self.duration)
        
        logger.debug(f"{self.name} took {self.duration*1000:.2f}ms")


class PerformanceMonitor:
    """Monitors application performance."""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            max_history: Maximum history size per metric
        """
        self.max_history = max_history
        self._timings: Dict[str, deque] = {}
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Callbacks
        self._threshold_callbacks: Dict[str, List[Callable]] = {}
    
    def record_timing(self, name: str, duration: float) -> None:
        """
        Record timing measurement.
        
        Args:
            name: Operation name
            duration: Duration in seconds
        """
        with self._lock:
            if name not in self._timings:
                self._timings[name] = deque(maxlen=self.max_history)
            self._timings[name].append(duration)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Increment a counter.
        
        Args:
            name: Counter name
            value: Increment value
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            self._counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """
        Set a gauge value.
        
        Args:
            name: Gauge name
            value: Gauge value
        """
        with self._lock:
            self._gauges[name] = value
    
    def get_stats(self, name: str) -> Optional[PerformanceStats]:
        """
        Get performance statistics.
        
        Args:
            name: Operation name
            
        Returns:
            Performance statistics or None
        """
        with self._lock:
            if name not in self._timings or not self._timings[name]:
                return None
            
            timings = list(self._timings[name])
            sorted_timings = sorted(timings)
            
            return PerformanceStats(
                operation=name,
                count=len(timings),
                total_time=sum(timings),
                min_time=min(timings),
                max_time=max(timings),
                avg_time=statistics.mean(timings),
                median_time=statistics.median(timings),
                p95_time=sorted_timings[int(len(timings) * 0.95)] if len(timings) > 1 else timings[0],
                p99_time=sorted_timings[int(len(timings) * 0.99)] if len(timings) > 1 else timings[0]
            )
    
    def get_all_stats(self) -> Dict[str, PerformanceStats]:
        """
        Get all performance statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = {}
        for name in self._timings:
            stat = self.get_stats(name)
            if stat:
                stats[name] = stat
        return stats
    
    def get_counters(self) -> Dict[str, int]:
        """Get all counters."""
        with self._lock:
            return self._counters.copy()
    
    def get_gauges(self) -> Dict[str, float]:
        """Get all gauges."""
        with self._lock:
            return self._gauges.copy()
    
    def reset(self, name: Optional[str] = None) -> None:
        """
        Reset metrics.
        
        Args:
            name: Optional specific metric to reset
        """
        with self._lock:
            if name:
                if name in self._timings:
                    self._timings[name].clear()
                if name in self._counters:
                    self._counters[name] = 0
                if name in self._gauges:
                    del self._gauges[name]
            else:
                self._timings.clear()
                self._counters.clear()
                self._gauges.clear()
    
    def timer(self, name: str) -> PerformanceTimer:
        """
        Create a timer context manager.
        
        Args:
            name: Operation name
            
        Returns:
            Timer context manager
        """
        return PerformanceTimer(name, self)
    
    def register_threshold(self, name: str, threshold: float,
                          callback: Callable[[str, float], None]) -> None:
        """
        Register threshold callback.
        
        Args:
            name: Metric name
            threshold: Threshold value
            callback: Callback function
        """
        if name not in self._threshold_callbacks:
            self._threshold_callbacks[name] = []
        
        def check_threshold(metric_name: str, value: float):
            if value > threshold:
                callback(metric_name, value)
        
        self._threshold_callbacks[name].append(check_threshold)
    
    def _check_thresholds(self, name: str, value: float) -> None:
        """Check and trigger threshold callbacks."""
        if name in self._threshold_callbacks:
            for callback in self._threshold_callbacks[name]:
                try:
                    callback(name, value)
                except Exception as e:
                    logger.error(f"Threshold callback error: {e}")


class SystemMonitor:
    """Monitors system resources."""
    
    def __init__(self):
        """Initialize system monitor."""
        self.process = psutil.Process()
    
    def get_cpu_usage(self) -> float:
        """
        Get CPU usage percentage.
        
        Returns:
            CPU usage percentage
        """
        return self.process.cpu_percent(interval=0.1)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage information.
        
        Returns:
            Memory usage dictionary
        """
        mem_info = self.process.memory_info()
        return {
            'rss': mem_info.rss,  # Resident Set Size
            'vms': mem_info.vms,  # Virtual Memory Size
            'rss_mb': mem_info.rss / 1024 / 1024,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'percent': self.process.memory_percent()
        }
    
    def get_thread_count(self) -> int:
        """
        Get thread count.
        
        Returns:
            Number of threads
        """
        return self.process.num_threads()
    
    def get_io_counters(self) -> Dict[str, Any]:
        """
        Get I/O counters.
        
        Returns:
            I/O statistics
        """
        try:
            io = self.process.io_counters()
            return {
                'read_count': io.read_count,
                'write_count': io.write_count,
                'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes
            }
        except:
            return {}
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            System information dictionary
        """
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            }
        }
    
    def get_process_info(self) -> Dict[str, Any]:
        """
        Get process information.
        
        Returns:
            Process information dictionary
        """
        return {
            'pid': self.process.pid,
            'name': self.process.name(),
            'status': self.process.status(),
            'create_time': self.process.create_time(),
            'cpu_percent': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'threads': self.get_thread_count(),
            'io': self.get_io_counters()
        }


class MetricsCollector:
    """Collects and aggregates metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.performance_monitor = PerformanceMonitor()
        self.system_monitor = SystemMonitor()
        self._metrics: List[Metric] = []
        self._lock = threading.Lock()
        self._collection_thread: Optional[threading.Thread] = None
        self._running = False
        self._collection_interval = 60.0  # seconds
    
    def start_collection(self, interval: float = 60.0) -> None:
        """
        Start metrics collection.
        
        Args:
            interval: Collection interval in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._collection_interval = interval
        self._collection_thread = threading.Thread(
            target=self._collect_loop,
            daemon=True
        )
        self._collection_thread.start()
        logger.info(f"Started metrics collection (interval: {interval}s)")
    
    def stop_collection(self) -> None:
        """Stop metrics collection."""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2.0)
        logger.info("Stopped metrics collection")
    
    def _collect_loop(self) -> None:
        """Collection loop."""
        while self._running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            
            time.sleep(self._collection_interval)
    
    def _collect_metrics(self) -> None:
        """Collect current metrics."""
        timestamp = time.time()
        
        # Collect system metrics
        process_info = self.system_monitor.get_process_info()
        
        metrics = [
            Metric("cpu_percent", process_info['cpu_percent'], timestamp, "%"),
            Metric("memory_rss", process_info['memory']['rss_mb'], timestamp, "MB"),
            Metric("thread_count", process_info['threads'], timestamp, "threads")
        ]
        
        # Collect performance metrics
        for name, stats in self.performance_monitor.get_all_stats().items():
            metrics.append(
                Metric(f"perf_{name}_avg", stats.avg_time * 1000, timestamp, "ms")
            )
            metrics.append(
                Metric(f"perf_{name}_p95", stats.p95_time * 1000, timestamp, "ms")
            )
        
        # Collect counters
        for name, value in self.performance_monitor.get_counters().items():
            metrics.append(
                Metric(f"counter_{name}", value, timestamp, "count")
            )
        
        # Store metrics
        with self._lock:
            self._metrics.extend(metrics)
            # Keep only last hour of metrics
            cutoff = timestamp - 3600
            self._metrics = [m for m in self._metrics if m.timestamp > cutoff]
    
    def get_metrics(self, since: Optional[float] = None) -> List[Metric]:
        """
        Get collected metrics.
        
        Args:
            since: Optional timestamp to get metrics since
            
        Returns:
            List of metrics
        """
        with self._lock:
            if since:
                return [m for m in self._metrics if m.timestamp > since]
            return self._metrics.copy()
    
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus formatted metrics
        """
        lines = []
        
        for metric in self.get_metrics():
            # Format: metric_name{tags} value timestamp
            tags_str = ""
            if metric.tags:
                tags_str = "{" + ",".join(f'{k}="{v}"' for k, v in metric.tags.items()) + "}"
            
            lines.append(f"{metric.name}{tags_str} {metric.value} {int(metric.timestamp * 1000)}")
        
        return "\n".join(lines)


# Global instances
performance_monitor = PerformanceMonitor()
system_monitor = SystemMonitor()
metrics_collector = MetricsCollector()


def timer(name: str) -> PerformanceTimer:
    """
    Create a timer context manager.
    
    Args:
        name: Operation name
        
    Returns:
        Timer context manager
    """
    return performance_monitor.timer(name)


def record_timing(name: str, duration: float) -> None:
    """
    Record timing measurement.
    
    Args:
        name: Operation name
        duration: Duration in seconds
    """
    performance_monitor.record_timing(name, duration)


def increment_counter(name: str, value: int = 1) -> None:
    """
    Increment a counter.
    
    Args:
        name: Counter name
        value: Increment value
    """
    performance_monitor.increment_counter(name, value)


def get_performance_stats() -> Dict[str, PerformanceStats]:
    """
    Get performance statistics.
    
    Returns:
        Dictionary of statistics
    """
    return performance_monitor.get_all_stats()