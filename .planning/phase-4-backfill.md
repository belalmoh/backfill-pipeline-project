# Phase 4: Backfill Integration - Detailed Plan

## Status: Not Started
## Estimated Duration: 2-3 days
## Priority: Medium (after Phase 3)

---

## Goals
1. Batch backfill script finalized
2. Streaming offset replay script
3. Hybrid backfill approach
4. Idempotency verified
5. Monitoring added
6. Runbook documented

---

## Task Breakdown

### 4.1 Batch Backfill Script Finalized
**Status:** Pending
**Files:** `scripts/backfill-batch.sh`

**Steps:**
1. Add error handling (set -e)
2. Add logging
3. Add progress output
4. Add color output
5. Test various date ranges

**Script:**
```bash
#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DAG_ID="clickstream_batch_dag"
START_DATE="${1:-}"
END_DATE="${2:-}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ -z "$START_DATE" ] || [ -z "$END_DATE" ]; then
    log_error "Usage: $0 <start_date> <end_date>"
    log_info "Example: $0 2024-01-01 2024-03-21"
    exit 1
fi

log_info "Starting batch backfill from $START_DATE to $END_DATE"

# Calculate date range
start=$(date -d "$START_DATE" +%s)
end=$(date -d "$END_DATE" +%s)
days=$(( (end - start) / 86400 + 1 ))
log_info "Backfilling $days days"

# Airflow backfill
log_info "Triggering Airflow backfill..."
if ! airflow dags backfill "$DAG_ID" \
    -s "$START_DATE" \
    -e "$END_DATE" \
    --rerun-failed \
    --local; then
    log_error "Airflow backfill failed"
    exit 1
fi

# Wait for completion
log_info "Waiting for backfill to complete..."
wait_for_backfill() {
    local status=$(airflow dags state "$DAG_ID" "$END_DATE" | tail -1)
    if [ "$status" == "success" ]; then
        return 0
    else
        sleep 30
        wait_for_backfill
    fi
}

# Verify
log_info "Verifying backfill..."
if ! python scripts/verify-backfill.py \
    --start-date "$START_DATE" \
    --end-date "$END_DATE"; then
    log_error "Backfill verification failed"
    exit 1
fi

log_info "Batch backfill complete ✓"
```

**Acceptance Criteria:**
- [ ] Script executable
- [ ] Error handling works
- [ ] Logging informative
- [ ] Progress shown
- [ ] Exit codes correct

---

### 4.2 Streaming Offset Replay
**Status:** Pending
**Files:** `scripts/backfill-streaming.sh`

**Steps:**
1. Stop Flink job gracefully
2. Create savepoint
3. Reset Kafka consumer group
4. Restart Flink from savepoint
5. Verify offset reset

**Script:**
```bash
#!/bin/bash
set -euo pipefail

TOPIC="dbserver1.public.clicks"
CONSUMER_GROUP="flink-consumer"
RESET_MODE="${1:-earliest}"  # earliest, latest, offset

if [ -z "$RESET_MODE" ]; then
    echo "Usage: $0 <earliest|latest|offset>"
    exit 1
fi

echo "Stopping Flink job..."
JOB_ID=$(flink list | grep "ClickStream" | awk '{print $4}')

if [ -z "$JOB_ID" ]; then
    echo "No running Flink job found"
    exit 1
fi

# Create savepoint
SAVEPOINT_PATH=$(flink cancel -s s3://clickstream-silver/flink-savepoints/ $JOB_ID | \
  grep "Savepoint" | awk '{print $NF}')

echo "Savepoint created: $SAVEPOINT_PATH"

echo "Resetting Kafka offsets..."
kafka-consumer-groups \
    --bootstrap-server kafka:9092 \
    --group $CONSUMER_GROUP \
    --topic $TOPIC \
    --reset-to-$RESET_MODE \
    --execute

echo "Restarting Flink job..."
flink run \
    -s $SAVEPOINT_PATH \
    /opt/flink/jobs/flink_job.jar

echo "Streaming backfill complete"
```

**Acceptance Criteria:**
- [ ] Flink job stops gracefully
- [ ] Savepoint created
- [ ] Offset reset
- [ ] Flink restarts
- [ ] Consumes from reset offset

---

### 4.3 Hybrid Approach
**Status:** Pending
**Files:** `scripts/backfill-hybrid.sh`

**Steps:**
1. Document strategy
2. Create script
3. Run batch for history
4. Switch to streaming
5. Verify no duplicates

**Strategy:**
```
Batch: Historical data (older than Kafka retention)
  ↓
Streaming: Current data (from now onward)
  ↓
Merge: Query both layers together
```

**Script:**
```bash
#!/bin/bash
set -euo pipefail

HISTORY_END_DATE="${1:-$(date -d '7 days ago' +%Y-%m-%d)}"

echo "Hybrid Backfill Strategy"
echo "========================"
echo "Batch: 2024-01-01 to $HISTORY_END_DATE"
echo "Stream: $HISTORY_END_DATE to present"
echo ""

# Step 1: Batch backfill for history
echo "Step 1: Running batch backfill for history..."
./scripts/backfill-batch.sh 2024-01-01 $HISTORY_END_DATE

# Step 2: Switch to streaming
echo "Step 2: Starting streaming pipeline..."
docker-compose exec flink-jobmanager flink run \
    /opt/flink/jobs/flink_job.jar

# Step 3: Verify no duplicates
echo "Step 3: Verifying no duplicates..."
python scripts/verify-no-duplicates.py

echo "Hybrid backfill complete"
```

**Acceptance Criteria:**
- [ ] Batch runs for history
- [ ] Streaming starts for current
- [ ] No duplicates at boundary
- [ ] Seamless handoff

---

### 4.4 Idempotency Verification
**Status:** Pending
**Files:** `scripts/verify-idempotency.py`, `tests/test_idempotency.py`

**Steps:**
1. Create verification script
2. Run backfill twice
3. Compare record counts
4. Compare data checksums
5. Assert identical results

**Script:**
```python
#!/usr/bin/env python3
"""
Verify idempotency: running backfill twice produces same result
"""

from pyspark.sql import SparkSession
import hashlib

def get_record_count(date):
    df = spark.read.parquet(f"s3a://clickstream-bronze/clicks/event_date={date}/")
    return df.count()

def get_data_checksum(date):
    df = spark.read.parquet(f"s3a://clickstream-bronze/clicks/event_date={date}/")
    data = df.collect()
    checksum = hashlib.md5(str(sorted(data)).encode()).hexdigest()
    return checksum

def verify_idempotency(start_date, end_date):
    # First run
    run_backfill(start_date, end_date)
    counts1 = get_counts(start_date, end_date)
    checksums1 = get_checksums(start_date, end_date)
    
    # Second run
    run_backfill(start_date, end_date)
    counts2 = get_counts(start_date, end_date)
    checksums2 = get_checksums(start_date, end_date)
    
    # Compare
    assert counts1 == counts2, "Record counts differ"
    assert checksums1 == checksums2, "Data checksums differ"
    
    print("✓ Idempotency verified")
    return True
```

**Acceptance Criteria:**
- [ ] First and second run produce same count
- [ ] Data checksums match
- [ ] No duplicates created
- [ ] Test automated

---

### 4.5 Backfill Monitoring
**Status:** Pending
**Files:** `scripts/monitor-backfill.py`

**Steps:**
1. Add logging to scripts
2. Track progress (records)
3. Track duration
4. Output summary
5. Log to file

**Monitoring:**
```python
#!/usr/bin/env python3
"""
Monitor backfill progress
"""

import time
from datetime import datetime

def monitor_backfill(start_date, end_date):
    start_time = time.time()
    dates = get_date_range(start_date, end_date)
    
    for i, date in enumerate(dates):
        status = get_task_status(date)
        records = get_record_count(date)
        elapsed = time.time() - start_time
        
        print(f"[{i+1}/{len(dates)}] {date}: "
              f"status={status}, records={records}, "
              f"elapsed={elapsed:.1f}s")
        
        # Log to file
        with open("backfill.log", "a") as f:
            f.write(f"{datetime.now()},{date},{status},{records}\n")
    
    # Summary
    duration = time.time() - start_time
    total_records = sum(get_record_count(d) for d in dates)
    
    print(f"\nBackfill Summary:")
    print(f"  Dates: {len(dates)}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Total records: {total_records}")
    print(f"  Rate: {total_records/duration:.1f} records/s")
```

**Acceptance Criteria:**
- [ ] Progress shown during backfill
- [ ] Records tracked
- [ ] Duration tracked
- [ ] Summary output
- [ ] Logged to file

---

### 4.6 Documentation & Runbook
**Status:** Pending
**Files:** `docs/backfill-runbook.md`

**Steps:**
1. Create runbook
2. Document batch steps
3. Document streaming steps
4. Document hybrid approach
5. Add troubleshooting
6. Add FAQ

**Runbook Structure:**
```markdown
# Backfill Runbook

## When to Backfill
- Initial deployment
- Bug fix requiring reprocess
- Schema change
- Data quality issue

## Batch Backfill
### Steps
1. Run: ./scripts/backfill-batch.sh 2024-01-01 2024-03-21
2. Monitor: Check Airflow UI
3. Verify: Run verification script

## Streaming Backfill
### Steps
1. Stop Flink job
2. Reset Kafka offset
3. Restart Flink

## Hybrid Approach
### When to Use
- Large historical backfill + real-time current
- Kafka retention limited

## Troubleshooting
### Common Issues
- Backfill stuck: Check Airflow logs
- Duplicates: Verify idempotency
- Missing data: Check date range
```

**Acceptance Criteria:**
- [ ] Runbook created
- [ ] All scenarios covered
- [ ] Troubleshooting section
- [ ] FAQ included
- [ ] Examples provided

---

## Dependencies

```
2.5 Backfill Script (Phase 2)
    ↓
4.1 Batch Finalized
    ↓
4.2 Streaming Offset
    ↓
4.3 Hybrid Approach
    ↓
4.4 Idempotency
    ↓
4.5 Monitoring
    ↓
4.6 Runbook
```

---

## Testing Strategy

### Manual Tests
```bash
# Test batch backfill
./scripts/backfill-batch.sh 2024-01-01 2024-01-10

# Test idempotency
./scripts/backfill-batch.sh 2024-01-01 2024-01-10
./scripts/backfill-batch.sh 2024-01-01 2024-01-10
# Verify same result

# Test streaming offset
./scripts/backfill-streaming.sh earliest

# Test hybrid
./scripts/backfill-hybrid.sh 2024-03-15
```

### Automated Tests
```python
# tests/test_phase4.py
def test_batch_backfill_runs():
    result = run_batch_backfill("2024-01-01", "2024-01-10")
    assert result.exit_code == 0

def test_idempotency():
    verify_idempotency("2024-01-01", "2024-01-10")

def test_streaming_offset_reset():
    reset_offset("earliest")
    assert offset_is_earliest()

def test_hybrid_no_duplicates():
    run_hybrid_backfill()
    assert no_duplicates()
```

---

## Deliverables Checklist

- [ ] `scripts/backfill-batch.sh` - Finalized batch script
- [ ] `scripts/backfill-streaming.sh` - Streaming offset script
- [ ] `scripts/backfill-hybrid.sh` - Hybrid script
- [ ] `scripts/verify-idempotency.py` - Idempotency verification
- [ ] `scripts/monitor-backfill.py` - Monitoring script
- [ ] `docs/backfill-runbook.md` - Runbook documentation
- [ ] `tests/test_phase4.py` - Phase 4 tests

---

## Definition of Done

### Functional
- [ ] All backfill scripts executable
- [ ] Running twice produces same result
- [ ] Monitoring shows progress
- [ ] Runbook documents all scenarios

### Documentation
- [ ] Runbook complete
- [ ] Troubleshooting guide
- [ ] FAQ section
- [ ] Examples provided

### Code Quality
- [ ] Scripts well-commented
- [ ] Error handling
- [ ] Logging informative
- [ ] No duplication

---

## Troubleshooting

### Batch Backfill Stuck
```bash
# Check Airflow UI
open http://localhost:8080

# Check task state
airflow tasks state clickstream_batch_dag extract_clicks 2024-01-01

# Retry
airflow tasks retry clickstream_batch_dag extract_clicks 2024-01-01
```

### Streaming Offset Reset Fails
```bash
# Check consumer group
kafka-consumer-groups --bootstrap-server kafka:9092 --list

# Check offset
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group flink-consumer --topic clicks --describe

# Force reset
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group flink-consumer --topic clicks \
  --reset-to-earliest --execute
```

### Duplicates Detected
```python
# Find duplicates
df.groupBy("click_id").count().filter(col("count") > 1).show()

# Deduplicate
df.dropDuplicates(["click_id"])

# Fix idempotency script
# Check partition overwrite logic
```

### Hybrid Handoff Issue
```bash
# Check boundary date
# Ensure batch ends before streaming starts
# Verify no gap, no overlap

# Query both layers
SELECT * FROM bronze WHERE date < '2024-03-15'
UNION ALL
SELECT * FROM silver WHERE date >= '2024-03-15'
```

---

## Next Steps

After Phase 4 complete:
1. Demo backfill capabilities
2. Show idempotency verification
3. Proceed to Phase 5 (Production Hardening)

---

## Estimated Effort

| Task | Hours |
|------|-------|
| 4.1 Batch Finalized | 2 |
| 4.2 Streaming Offset | 2 |
| 4.3 Hybrid Approach | 3 |
| 4.4 Idempotency | 2 |
| 4.5 Monitoring | 2 |
| 4.6 Runbook | 2 |
| Testing & Debugging | 3 |
| **Total** | **16 hours** |

---

## Notes

- Idempotency is critical for production
- Hybrid approach most realistic for real-world
- Monitoring often overlooked but essential
- Runbook shows operational maturity
- Backfill is key interview talking point
