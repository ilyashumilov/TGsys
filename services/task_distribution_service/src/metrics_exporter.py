"""
Prometheus metrics exporter for Task Distribution Service.
"""

import time
import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Gauge, Histogram, start_http_server


class TaskDistributionMetrics:
    """Prometheus metrics for task distribution service."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # Prometheus metrics
        self.pending_tasks_gauge = Gauge(
            'tgsys_pending_tasks_total',
            'Total number of pending tasks in queue'
        )
        
        self.active_workers_gauge = Gauge(
            'tgsys_active_workers_total',
            'Total number of active workers'
        )
        
        self.tasks_assigned_counter = Counter(
            'tgsys_tasks_assigned_total',
            'Total number of tasks assigned to workers'
        )
        
        self.tasks_completed_counter = Counter(
            'tgsys_tasks_completed_total',
            'Total number of tasks completed by workers'
        )
        
        self.task_assignment_duration = Histogram(
            'tgsys_task_assignment_duration_seconds',
            'Time taken to assign tasks to workers'
        )
        
        self.task_completion_duration = Histogram(
            'tgsys_task_completion_duration_seconds',
            'Time taken for workers to complete tasks'
        )
        
        self.worker_task_count = Gauge(
            'tgsys_worker_task_count',
            'Number of tasks assigned to each worker',
            ['worker_id']
        )
        
        self.available_accounts_gauge = Gauge(
            'tgsys_available_accounts_total',
            'Number of accounts available for task assignment'
        )
        
        self.busy_accounts_gauge = Gauge(
            'tgsys_busy_accounts_total',
            'Number of accounts currently busy with tasks'
        )
        
        self.avg_task_wait_time = Gauge(
            'tgsys_avg_task_wait_time_seconds',
            'Average time tasks wait in queue before assignment'
        )
        
        self.avg_task_processing_time = Gauge(
            'tgsys_avg_task_processing_time_seconds',
            'Average time for workers to process tasks'
        )
        
        self.task_success_rate = Gauge(
            'tgsys_task_success_rate',
            'Success rate of task processing (percentage)'
        )
        
        self.avg_account_health_score = Gauge(
            'tgsys_avg_account_health_score',
            'Average health score of all accounts'
        )
        
        # Track task wait times
        self.task_queue_times: Dict[str, float] = {}
        
    def start_server(self):
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(self.port)
            self.logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
            raise
    
    def update_pending_tasks(self, count: int):
        """Update pending tasks gauge."""
        self.pending_tasks_gauge.set(count)
        
        # Update average wait time
        if count > 0:
            # Simple calculation - in real implementation, track actual wait times
            self.avg_task_wait_time.set(min(count * 2.0, 300.0))  # Max 5 minutes
        else:
            self.avg_task_wait_time.set(0)
    
    def update_active_workers(self, count: int):
        """Update active workers gauge."""
        self.active_workers_gauge.set(count)
    
    def record_task_assignment(self, worker_id: str, assignment_time: float):
        """Record a task assignment."""
        self.tasks_assigned_counter.inc()
        self.task_assignment_duration.observe(assignment_time)
        
        # Update worker task count
        self.worker_task_count.labels(worker_id=worker_id).inc()
    
    def record_task_completion(self, worker_id: str, processing_time: float, success: bool = True):
        """Record a task completion."""
        self.tasks_completed_counter.inc()
        self.task_completion_duration.observe(processing_time)
        
        # Update worker task count
        current_count = self.worker_task_count.labels(worker_id=worker_id)._value._value
        if current_count > 0:
            self.worker_task_count.labels(worker_id=worker_id).set(current_count - 1)
        
        # Update success rate (simple moving average)
        current_rate = self.task_success_rate._value._value
        if success:
            new_rate = (current_rate * 0.9) + (100.0 * 0.1)  # 90% old, 10% new
        else:
            new_rate = (current_rate * 0.9) + (0.0 * 0.1)
        self.task_success_rate.set(new_rate)
        
        # Update average processing time
        current_avg = self.avg_task_processing_time._value._value
        new_avg = (current_avg * 0.9) + (processing_time * 0.1)
        self.avg_task_processing_time.set(new_avg)
    
    def update_account_availability(self, available: int, busy: int, avg_health: float):
        """Update account availability metrics."""
        self.available_accounts_gauge.set(available)
        self.busy_accounts_gauge.set(busy)
        self.avg_account_health_score.set(avg_health)
    
    def record_task_queued(self, task_id: str):
        """Record when a task is queued."""
        self.task_queue_times[task_id] = time.time()
    
    def record_task_assigned(self, task_id: str, worker_id: str):
        """Record when a task is assigned to a worker."""
        if task_id in self.task_queue_times:
            wait_time = time.time() - self.task_queue_times[task_id]
            self.record_task_assignment(worker_id, wait_time)
            del self.task_queue_times[task_id]


# Global metrics instance
_metrics_exporter: Optional[TaskDistributionMetrics] = None


def init_metrics_exporter(port: int = 8000) -> TaskDistributionMetrics:
    """Initialize the global metrics exporter."""
    global _metrics_exporter
    _metrics_exporter = TaskDistributionMetrics(port)
    _metrics_exporter.start_server()
    return _metrics_exporter


def get_metrics_exporter() -> Optional[TaskDistributionMetrics]:
    """Get the global metrics exporter."""
    return _metrics_exporter
