# Phase 5: Production Hardening - Detailed Plan

## Status: Not Started
## Estimated Duration: 2-3 days
## Priority: Low (after Phase 4, optional for interview)

---

## Goals
1. Metrics collection working
2. Alerts configured
3. Dashboard visible
4. Logs centralized
5. Performance benchmarks
6. Chaos tests passing

---

## Task Breakdown

### 5.1 Metrics Collection
**Status:** Pending
**Files:** `src/utils/metrics.py`, `src/batch/metrics.py`

**Steps:**
1. Instrument batch pipeline
2. Instrument streaming
3. Export metrics
4. Create dashboard queries
5. Track key metrics

**Metrics to Track:**
```python
# Batch metrics
- records_processed
- pipeline_duration_seconds
- partition_count
- dq_test_pass_rate

# Streaming metrics
- kafka_consumer_lag
- records_per_second
- checkpoint_duration
- watermark_delay
```

**Implementation:**
```python
from pyspark.sql import SparkSession
import time
import json

def run_with_metrics(job_name, func):
    start_time = time.time()
    result = func()
    duration = time.time() - start_time
    
    metrics = {
        "job": job_name,
        "timestamp": time.time(),
        "records_processed": result.count(),
        "duration_seconds": duration,
        "throughput": result.count() / duration
    }
    
    # Log metrics
    with open("metrics.log", "a") as f:
        f.write(json.dumps(metrics) + "\n")
    
    # Optional: send to Prometheus
    send_to_prometheus(metrics)
    
    return result
```

**Acceptance Criteria:**
- [ ] Metrics logged
- [ ] Throughput calculated
- [ ] Duration tracked
- [ ] Metrics queryable
- [ ] Dashboard shows metrics

---

### 5.2 Alerting
**Status:** Pending
**Files:** `docker/airflow/dags/alerting.py`

**Steps:**
1. Configure Airflow email
2. Set up Slack webhook
3. Create alert rules
4. Test triggers
5. Document response

**Configuration:**
```python
# Airflow alerting
default_args = {
    'email': ['data-team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}

# Slack alert
def send_slack_alert(context):
    import requests
    
    webhook_url = "https://hooks.slack.com/services/XXX/YYY/ZZZ"
    
    message = {
        "text": f"Pipeline Failed: {context['task_id']}",
        "attachments": [{
            "color": "danger",
            "fields": [{
                "title": "Error",
                "value": str(context['exception']),
                "short": False
            }]
        }]
    }
    
    requests.post(webhook_url, json=message)
```

**Acceptance Criteria:**
- [ ] Email alerts configured
- [ ] Slack alerts working
- [ ] Alert triggers on failure
- [ ] Alert informative
- [ ] Response documented

---

### 5.3 Dashboard
**Status:** Pending
**Files:** `docs/dashboard.md`

**Steps:**
1. Create Grafana dashboard (optional)
2. Or use Airflow UI
3. Show pipeline status
4. Show data volume
5. Show latency

**Grafana Panels:**
```
Panel 1: Pipeline Status
- Status: Running/Failed/Success
- Last run time
- Next scheduled run

Panel 2: Data Volume
- Records processed (time series)
- Batch vs Streaming volume

Panel 3: Latency
- Batch duration
- Streaming lag
- Data freshness

Panel 4: Data Quality
- DQ test pass rate
- Failed expectations
```

**Acceptance Criteria:**
- [ ] Dashboard accessible
- [ ] Shows real-time status
- [ ] Shows volume
- [ ] Shows latency
- [ ] Refreshes automatically

---

### 5.4 Log Aggregation
**Status:** Pending
**Files:** `config/logging.yaml`

**Steps:**
1. Configure log paths
2. Centralize logs
3. Add structured logging
4. Include job_id, batch_id
5. Make searchable

**Structured Logging:**
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "job_id": getattr(record, 'job_id', 'unknown'),
            "batch_id": getattr(record, 'batch_id', 'unknown')
        }
        return json.dumps(log_entry)

# Configure
handler = logging.FileHandler('pipeline.log')
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

**Acceptance Criteria:**
- [ ] Logs structured (JSON)
- [ ] Job ID included
- [ ] Batch ID included
- [ ] Logs centralized
- [ ] Searchable

---

### 5.5 Performance Tuning
**Status:** Pending
**Files:** `docs/performance.md`

**Steps:**
1. Benchmark batch pipeline
2. Tune Spark parallelism
3. Tune Flink parallelism
4. Document characteristics
5. Identify bottlenecks

**Benchmark:**
```python
# Benchmark batch
def benchmark_batch():
    start = time.time()
    run_batch_job()
    duration = time.time() - start
    
    print(f"Batch duration: {duration:.1f}s")
    print(f"Records/second: {record_count/duration:.1f}")
    
    # Tune Spark
    # spark.default.parallelism = cores * 2
    # spark.executor.memory = 4G
    # spark.executor.cores = 2
```

**Flink Tuning:**
```yaml
# flink-conf.yaml
taskmanager.numberOfTaskSlots: 4
taskmanager.memory.process.size: 2048m
jobmanager.memory.process.size: 1024m
parallelism.default: 4
```

**Acceptance Criteria:**
- [ ] Baseline benchmark
- [ ] Spark tuned
- [ ] Flink tuned
- [ ] Performance documented
- [ ] Bottlenecks identified

---

### 5.6 Chaos Testing
**Status:** Pending
**Files:** `tests/test_chaos.py`

**Steps:**
1. Kill worker during pipeline
2. Simulate Kafka outage
3. Simulate MinIO outage
4. Verify recovery
5. Document scenarios

**Chaos Tests:**
```python
def test_worker_kill():
    """Test pipeline recovers from worker death"""
    # Start pipeline
    start_pipeline()
    
    # Kill worker
    kill_spark_worker()
    
    # Wait for retry
    wait_for_recovery()
    
    # Verify completion
    assert pipeline_completed()

def test_kafka_outage():
    """Test Flink handles Kafka outage"""
    # Start Flink
    start_flink()
    
    # Stop Kafka
    stop_kafka()
    
    # Wait
    time.sleep(60)
    
    # Start Kafka
    start_kafka()
    
    # Verify Flink recovered
    assert flink_consuming_messages()

def test_minio_outage():
    """Test pipeline handles MinIO outage"""
    # Start pipeline
    start_pipeline()
    
    # Stop MinIO
    stop_minio()
    
    # Wait
    time.sleep(60)
    
    # Start MinIO
    start_minio()
    
    # Verify recovery
    assert pipeline_completed()
```

**Acceptance Criteria:**
- [ ] Worker kill test passes
- [ ] Kafka outage test passes
- [ ] MinIO outage test passes
- [ ] Recovery automatic
- [ ] No data loss

---

## Dependencies

```
4.5 Monitoring (Phase 4)
    ↓
5.1 Metrics
    ↓
5.2 Alerting
    ↓
5.3 Dashboard
    ↓
5.4 Logging
    ↓
5.5 Performance
    ↓
5.6 Chaos Tests
```

---

## Testing Strategy

### Manual Tests
```bash
# Test metrics logging
python src/utils/metrics.py

# Test alerting
python -c "from src.utils.alerting import send_test_alert"

# Test dashboard
open http://localhost:3000  # Grafana

# Test chaos
python -m pytest tests/test_chaos.py -v
```

### Automated Tests
```python
# tests/test_phase5.py
def test_metrics_logged():
    assert metrics_logged()

def test_alerts_sent():
    send_alert()
    assert alert_received()

def test_dashboard_shows_data():
    data = get_dashboard_data()
    assert data['records'] > 0

def test_chaos_recovery():
    test_worker_kill()
    assert recovered()
```

---

## Deliverables Checklist

- [ ] `src/utils/metrics.py` - Metrics collection
- [ ] `src/utils/alerting.py` - Alerting utilities
- [ ] `docs/dashboard.md` - Dashboard guide
- [ ] `config/logging.yaml` - Logging config
- [ ] `docs/performance.md` - Performance benchmarks
- [ ] `tests/test_chaos.py` - Chaos tests
- [ ] `tests/test_phase5.py` - Phase 5 tests

---

## Definition of Done

### Functional
- [ ] Metrics collection working
- [ ] Alerts configured
- [ ] Dashboard visible
- [ ] Logs centralized
- [ ] Performance benchmarks
- [ ] Chaos tests passing

### Documentation
- [ ] Phase 5 README updated
- [ ] Dashboard guide
- [ ] Performance tuning guide
- [ ] Chaos testing guide

### Code Quality
- [ ] Code commented
- [ ] Error handling
- [ ] Logs informative
- [ ] Production-ready

---

## Troubleshooting

### Metrics Not Logged
```bash
# Check metrics.py
cat src/utils/metrics.py

# Check file permissions
ls -la metrics.log

# Test manually
python -c "from src.utils.metrics import log_metrics; log_metrics({'test': 1})"
```

### Alerts Not Sent
```bash
# Check SMTP config
cat .env | grep SMTP

# Test email
python -c "from airflow.utils.email import send_email; send_email(...)"

# Check Slack webhook
curl -X POST -H "Content-Type: application/json" \
  --data '{"text":"test"}' \
  https://hooks.slack.com/services/XXX/YYY/ZZZ
```

### Dashboard Not Showing Data
```bash
# Check data source
# (Prometheus, Grafana, or Airflow)

# Refresh dashboard
# (Force refresh)

# Check query
# (Verify query syntax)
```

### Chaos Test Fails
```bash
# Check test isolation
# (Ensure test doesn't affect other tests)

# Increase timeout
# (Recovery may take time)

# Check service health
# (Ensure service actually restarted)
```

---

## Next Steps

After Phase 5 complete:
1. Demo production features
2. Show chaos test recovery
3. Project complete!
4. Prepare for interview

---

## Estimated Effort

| Task | Hours |
|------|-------|
| 5.1 Metrics | 2 |
| 5.2 Alerting | 2 |
| 5.3 Dashboard | 2 |
| 5.4 Logging | 2 |
| 5.5 Performance | 2 |
| 5.6 Chaos Tests | 3 |
| Testing & Debugging | 3 |
| **Total** | **16 hours** |

---

## Notes

- Phase 5 optional for interview prep
- Focus on Phases 1-4 for core functionality
- Phase 5 shows production maturity
- Chaos testing impressive but not required
- Metrics/alerting most important for production
