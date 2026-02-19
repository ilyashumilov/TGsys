"""
Metrics collection and monitoring utilities for TGsys services.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe metrics collector for TGsys services."""
    
    def __init__(self, service_name: str, max_history: int = 1000):
        self.service_name = service_name
        self.max_history = max_history
        self.logger = logging.getLogger(__name__)
        
        # Thread-safe storage
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] += value
            self.logger.debug(f"Counter incremented: {name} += {value}")
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
            self.logger.debug(f"Gauge set: {name} = {value}")
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a value in a histogram."""
        with self._lock:
            key = self._make_key(name, tags)
            self._histograms[key].append(value)
            self.logger.debug(f"Histogram recorded: {name} = {value}")
    
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing value."""
        with self._lock:
            key = self._make_key(name, tags)
            self._timers[key].append(duration)
            self.logger.debug(f"Timer recorded: {name} = {duration}s")
    
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimerContext(self, name, tags)
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create a unique key from name and tags."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        with self._lock:
            summary = {
                "service": self.service_name,
                "timestamp": time.time(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "timers": {}
            }
            
            # Calculate histogram statistics
            for key, values in self._histograms.items():
                if values:
                    values_list = list(values)
                    summary["histograms"][key] = {
                        "count": len(values_list),
                        "sum": sum(values_list),
                        "min": min(values_list),
                        "max": max(values_list),
                        "avg": sum(values_list) / len(values_list)
                    }
            
            # Calculate timer statistics
            for key, durations in self._timers.items():
                if durations:
                    durations_list = list(durations)
                    summary["timers"][key] = {
                        "count": len(durations_list),
                        "sum": sum(durations_list),
                        "min": min(durations_list),
                        "max": max(durations_list),
                        "avg": sum(durations_list) / len(durations_list)
                    }
            
            return summary
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self.logger.info("All metrics reset")


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.name, duration, self.tags)


class BusinessMetrics:
    """Business-specific metrics for TGsys."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    def record_message_processed(self, channel_id: str, success: bool = True):
        """Record a message processing event."""
        tags = {"channel_id": channel_id, "success": str(success)}
        self.collector.increment_counter("messages_processed", tags=tags)
        if success:
            self.collector.increment_counter("messages_processed_success", tags=tags)
        else:
            self.collector.increment_counter("messages_processed_failed", tags=tags)
    
    def record_comment_posted(self, account_id: str, success: bool = True):
        """Record a comment posting event."""
        tags = {"account_id": account_id, "success": str(success)}
        self.collector.increment_counter("comments_posted", tags=tags)
        if success:
            self.collector.increment_counter("comments_posted_success", tags=tags)
        else:
            self.collector.increment_counter("comments_posted_failed", tags=tags)
    
    def record_account_health(self, account_id: str, health_score: int):
        """Record account health score."""
        tags = {"account_id": account_id}
        self.collector.set_gauge("account_health_score", health_score, tags=tags)
    
    def record_active_accounts(self, count: int):
        """Record number of active accounts."""
        self.collector.set_gauge("active_accounts_count", count)
    
    def record_queue_depth(self, queue_name: str, depth: int):
        """Record queue depth."""
        tags = {"queue": queue_name}
        self.collector.set_gauge("queue_depth", depth, tags=tags)
    
    def record_database_query(self, query_type: str, duration: float, success: bool = True):
        """Record database query metrics."""
        tags = {"query_type": query_type, "success": str(success)}
        self.collector.record_timer("database_query_duration", duration, tags=tags)
        self.collector.increment_counter("database_queries", tags=tags)
    
    def record_kafka_message(self, operation: str, topic: str, duration: float, success: bool = True):
        """Record Kafka message metrics."""
        tags = {"operation": operation, "topic": topic, "success": str(success)}
        self.collector.record_timer("kafka_message_duration", duration, tags=tags)
        self.collector.increment_counter("kafka_messages", tags=tags)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def init_metrics(service_name: str) -> MetricsCollector:
    """Initialize the global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(service_name)
    return _metrics_collector


def get_metrics() -> Optional[MetricsCollector]:
    """Get the global metrics collector."""
    return _metrics_collector


def track_business_metrics():
    """Get business metrics tracker."""
    if _metrics_collector is None:
        raise RuntimeError("Metrics not initialized. Call init_metrics() first.")
    return BusinessMetrics(_metrics_collector)
