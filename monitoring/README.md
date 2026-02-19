# TGsys Monitoring Dashboard

This directory contains the monitoring setup for TGsys, including Grafana dashboard and Prometheus configuration to track pending tasks and worker assignments.

## 📊 Dashboard Features

The Grafana dashboard provides comprehensive monitoring of:

### Task Management
- **Pending Tasks Queue** - Real-time count of tasks waiting for assignment
- **Current Pending Tasks** - Current number in queue with color coding
- **Task Assignment & Completion** - Timeline of task assignments and completions
- **Tasks per Worker** - Distribution of tasks across workers (pie chart)

### Worker Performance
- **Active Workers** - Number of currently active workers
- **Task Processing Rates** - Assignment and completion rates over time
- **Avg Task Wait Time** - How long tasks wait in queue
- **Avg Task Processing Time** - Time for workers to complete tasks

### Account Health
- **Account Availability** - Available vs busy accounts
- **Avg Account Health Score** - Overall health of account pool
- **Task Success Rate** - Percentage of successful task completions

## 🚀 Quick Start

### 1. Start the Monitoring Stack
```bash
./start-monitoring.sh
```

### 2. Access the Dashboard
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
- **Prometheus**: http://localhost:9090
- **Task Metrics**: http://localhost:8000/metrics

### 3. Import the Dashboard
1. Go to Grafana → Dashboards → Import
2. Upload `monitoring/grafana-dashboard.json`
3. Select Prometheus as the data source

## 📈 Available Metrics

The following Prometheus metrics are exposed:

### Task Metrics
- `tgsys_pending_tasks_total` - Total pending tasks in queue
- `tgsys_tasks_assigned_total` - Total tasks assigned to workers
- `tgsys_tasks_completed_total` - Total tasks completed
- `tgsys_task_assignment_duration_seconds` - Time to assign tasks
- `tgsys_task_completion_duration_seconds` - Time to complete tasks

### Worker Metrics
- `tgsys_active_workers_total` - Number of active workers
- `tgsys_worker_task_count` - Tasks per worker (labeled by worker_id)

### Account Metrics
- `tgsys_available_accounts_total` - Available accounts for tasks
- `tgsys_busy_accounts_total` - Currently busy accounts
- `tgsys_avg_account_health_score` - Average health score

### Performance Metrics
- `tgsys_avg_task_wait_time_seconds` - Average queue wait time
- `tgsys_avg_task_processing_time_seconds` - Average processing time
- `tgsys_task_success_rate` - Task success percentage

## 🔧 Configuration

### Prometheus Configuration
- **Config File**: `monitoring/prometheus.yml`
- **Scrape Interval**: 15 seconds
- **Data Retention**: 200 hours
- **Port**: 9090

### Grafana Configuration
- **Dashboard**: `monitoring/grafana-dashboard.json`
- **Datasource**: `monitoring/grafana-datasource.yml`
- **Port**: 3000
- **Admin Password**: `admin`

### Task Distribution Service
- **Metrics Port**: 8000
- **Metrics Endpoint**: `/metrics`
- **Update Frequency**: Real-time

## 📝 Dashboard Panels

### Row 1: Overview
- **Pending Tasks Queue** - Time series of pending tasks
- **Current Pending Tasks** - Current count with thresholds
- **Active Workers** - Current number of active workers

### Row 2: Task Distribution
- **Task Assignment & Completion** - Dual line chart
- **Tasks per Worker** - Pie chart distribution

### Row 3: Performance
- **Task Processing Rates** - Assignment and completion rates
- **Account Availability** - Available vs busy accounts

### Row 4: Statistics
- **Avg Task Wait Time** - Current wait time
- **Avg Task Processing Time** - Current processing time
- **Task Success Rate** - Success percentage
- **Avg Account Health** - Average health score

## 🎯 Alerting (Future)

The dashboard is configured for visual alerting with color thresholds:

- **Pending Tasks**: Green (<10), Yellow (10-50), Red (>50)
- **Task Wait Time**: Green (<30s), Yellow (30-120s), Red (>120s)
- **Processing Time**: Green (<60s), Yellow (60-300s), Red (>300s)
- **Success Rate**: Green (>90%), Yellow (70-90%), Red (<70%)
- **Account Health**: Green (>80), Yellow (50-80), Red (<50)

## 🔍 Troubleshooting

### No Data in Dashboard
1. Ensure the task distribution service is running
2. Check if metrics are available at http://localhost:8000/metrics
3. Verify Prometheus is scraping: http://localhost:9090/targets
4. Check Grafana datasource connection

### Metrics Not Updating
1. Restart the task distribution service
2. Check logs for metric export errors
3. Verify network connectivity between services

### Dashboard Import Issues
1. Ensure Grafana is running (http://localhost:3000)
2. Check dashboard JSON format
3. Verify Prometheus datasource is configured

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [TGsys Architecture](../README_Architecture.md)
- [Task Distribution Service](../services/task_distribution_service/)

## 🛠️ Customization

### Adding New Metrics
1. Update `metrics_exporter.py` in the task distribution service
2. Add corresponding panels to the Grafana dashboard JSON
3. Restart services to apply changes

### Modifying Dashboard
1. Edit `monitoring/grafana-dashboard.json`
2. Or use Grafana UI to modify and export
3. Update the file for persistence

### Changing Thresholds
1. Edit the threshold values in the dashboard JSON
2. Modify color schemes as needed
3. Update alert rules if configured
