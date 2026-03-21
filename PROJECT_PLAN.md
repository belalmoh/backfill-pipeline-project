# Clickstream Analytics Pipeline - Production Architecture

## Project Overview

**Goal:** Build a production-grade data pipeline with both batch and streaming processing, implementing robust backfill strategies for initial deployment and late-arriving data.

**Business Domain:** E-commerce Clickstream Analytics
- Track user clicks, page views, sessions
- Analyze user behavior, conversion funnels
- Real-time dashboards + historical reporting

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Clickstream Analytics Architecture                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                                                        │
│  │  PostgreSQL  │  (Source - Transactional DB)                          │
│  │  (clicks,    │                                                        │
│  │   sessions)  │                                                        │
│  └──────┬───────┘                                                        │
│         │                                                                 │
│         ├────────────────────────────────┐                                │
│         │                                │                                │
│         ▼                                ▼                                │
│  ┌───────────────┐              ┌───────────────┐                        │
│  │   Batch       │              │   Streaming   │                        │
│  │   Extract     │              │   Ingestion   │                        │
│  │   (CDC)       │              │   (Kafka)     │                        │
│  │               │              │               │                        │
│  │  Airflow      │              │  Kafka        │                        │
│  │  + Spark      │              │  + Flink      │                        │
│  └──────┬────────┘              └──────┬────────┘                        │
│         │                               │                                 │
│         │                               │                                 │
│         ▼                               ▼                                 │
│  ┌─────────────────────────────────────────────────┐                      │
│  │              MinIO Data Lake                    │                      │
│  │                                                 │                      │
│  │  /bronze/           /silver/          /gold/    │                      │
│  │  ├─ batch/          ├─ batch/         ├─ agg/   │                      │
│  │  │  └─ clicks/      │  └─ clicks/     │  └─ by_date/                  │
│  │  └─ streaming/      └─ streaming/     └─ by_user/                      │
│  │     └─ clicks/         └─ clicks/                                     │
│  └─────────────────────────────────────────────────┘                      │
│         │                                                                 │
│         ▼                                                                 │
│  ┌───────────────┐                                                        │
│  │   Analytics   │  (Destination - Queries, Dashboards)                  │
│  │   Engine      │                                                        │
│  │   (Presto/    │                                                        │
│  │    Spark SQL) │                                                        │
│  └───────────────┘                                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Source DB** | PostgreSQL | Clickstream events, sessions |
| **Orchestration** | Apache Airflow | Batch pipeline scheduling, backfill triggers |
| **Batch Processing** | Apache Spark | CDC extraction, transformation, aggregation |
| **Streaming** | Apache Kafka + Flink | Real-time ingestion, windowed aggregations |
| **Message Queue** | Apache Kafka | Event streaming, buffering |
| **Data Lake** | MinIO (S3-compatible) | Bronze/Silver/Gold layers (Parquet) |
| **Schema Registry** | Confluent Schema Registry | Schema versioning, evolution |
| **Data Quality** | Great Expectations | Validation, testing |

---

## Data Model

### Source Tables (PostgreSQL)

```sql
-- Clickstream events
CREATE TABLE clicks (
    click_id          BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    session_id        VARCHAR(100) NOT NULL,
    page_url          TEXT NOT NULL,
    event_type        VARCHAR(50),  -- 'page_view', 'click', 'scroll', 'purchase'
    event_timestamp   TIMESTAMP NOT NULL,
    user_agent        TEXT,
    ip_address        INET,
    referrer_url      TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for CDC
CREATE INDEX idx_clicks_updated_at ON clicks(updated_at);
CREATE INDEX idx_clicks_event_timestamp ON clicks(event_timestamp);

-- Sessions (denormalized for analytics)
CREATE TABLE sessions (
    session_id        VARCHAR(100) PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    started_at        TIMESTAMP NOT NULL,
    ended_at          TIMESTAMP,
    duration_seconds  INT,
    page_views_count  INT DEFAULT 0,
    bounce            BOOLEAN DEFAULT false,
    traffic_source    VARCHAR(50),  -- 'organic', 'paid', 'direct', 'referral'
    device_type       VARCHAR(50),  -- 'desktop', 'mobile', 'tablet'
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Target Schema (MinIO - Parquet)

```
/minio-data-lake/
├── bronze/
│   ├── clicks/
│   │   ├── extract_date=2024-01-01/
│   │   │   └── part-00001.parquet
│   │   └── extract_date=2024-01-02/
│   └── sessions/
├── silver/
│   ├── clicks/
│   │   ├── event_date=2024-01-01/
│   │   └── event_date=2024-01-02/
│   └── sessions/
└── gold/
    ├── daily_metrics/
    │   ├── date=2024-01-01/
    │   └── date=2024-01-02/
    └── user_sessions/
        ├── user_id=1001/
        └── user_id=1002/
```

---

## Pipeline Components

### 1. Batch Pipeline (Airflow + Spark)

**Purpose:** Historical backfill, daily incremental loads, CDC

**DAG Structure:**
```
[extract_clicks_cdc] → [validate_quality] → [transform_silver] → [aggregate_gold]
       ↓                      ↓                    ↓                    ↓
   [Bronze]              [DQ Tests]            [Silver]              [Gold]
```

**Key Features:**
- Incremental extract using `updated_at` watermark
- Idempotent writes (delete + insert per partition)
- Schema evolution handling
- Great Expectations validation

---

### 2. Streaming Pipeline (Kafka + Flink)

**Purpose:** Real-time ingestion, low-latency analytics

**Architecture:**
```
PostgreSQL ──▶ Kafka Connect (CDC) ──▶ Kafka Topic (clicks) ──▶ Flink ──▶ MinIO
     │                                    │                        │
     │                                    │                        │
     └─────────────── Backfill ────────────┴────────────────────────┘
                     (Batch or Offset Replay)
```

**Key Features:**
- Exactly-once semantics (Flink checkpoints + transactional sink)
- Schema registry integration
- Watermark for late data
- Windowed aggregations (optional)
- Atomic file commits via Flink StreamingFileSink

---

## Backfill Strategies

### Strategy 1: Initial Deployment Backfill

**Scenario:** Pipeline deployed March 21, need data from Jan 1

**Batch Approach:**
```python
# Airflow backfill command
airflow backfill -s 2024-01-01 -e 2024-03-20 clickstream_batch_dag

# What happens:
# 1. For each date in range:
#    - Extract data WHERE updated_at::date = {{ date }}
#    - Transform and validate
#    - Write to partition extract_date={{ date }}
# 2. Idempotent: safe to re-run
```

**Streaming Approach:**
```bash
# Option A: Kafka offset replay (if within retention)
kafka-consumer-groups --bootstrap localhost:9092 \
  --group flink-consumer \
  --topic clicks \
  --reset-to-earliest \
  --execute

# Option B: Batch backfill + stream continue
# 1. Run batch backfill for history (older than retention)
# 2. Streaming picks up from current offset
```

---

### Strategy 2: Late-Arriving Data Handling

**Scenario:** Click event from March 15 arrives on March 21 (delayed)

**Batch Handling:**
```python
# Airflow task checks for late data
def extract_with_late_data(execution_date):
    # Primary extract: data updated on execution_date
    primary = extract_cdc(execution_date)
    
    # Late data: data from past 7 days updated today
    late = extract_late_data(
        start_date=execution_date - timedelta(days=7),
        end_date=execution_date
    )
    
    return primary.union(late)
```

**Streaming Handling:**
```java
// Flink watermark for late data
DataStream<Click> clicks = env
    .addSource(kafkaSource)
    .assignTimestampsAndWatermarks(
        WatermarkStrategy
            .<Click>forBoundedOutOfOrderness(Duration.ofMinutes(10))
            .withTimestampAssigner((event, timestamp) -> event.getEventTimestamp())
    );

// Allows 10 minutes late data
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goals:** Infrastructure setup, basic batch pipeline

**Tasks:**
1. ✅ Set up PostgreSQL with sample clickstream data
2. ✅ Set up MinIO (S3-compatible storage)
3. ✅ Set up Kafka + Schema Registry
4. ✅ Create Airflow DAG for batch extraction
5. ✅ Implement Spark batch job (extract → bronze)
6. ✅ Implement idempotent writes

**Deliverables:**
- Docker Compose for all services
- Sample data generator (100K clicks)
- Basic batch pipeline (Bronze layer)

---

### Phase 2: Batch Pipeline Complete (Week 3-4)

**Goals:** Full batch pipeline with transformations, DQ testing

**Tasks:**
1. ✅ Silver layer transformations (cleaning, enrichment)
2. ✅ Gold layer aggregations (daily metrics, user sessions)
3. ✅ Great Expectations integration
4. ✅ Schema evolution handling
5. ✅ Backfill implementation
6. ✅ Airflow error handling + alerting

**Deliverables:**
- Complete batch pipeline (Bronze → Silver → Gold)
- Data quality test suite
- Backfill script/command
- Error handling + retry logic

---

### Phase 3: Streaming Pipeline (Week 5-6)

**Goals:** Real-time ingestion with Flink

**Tasks:**
1. ✅ Kafka Connect CDC setup (PostgreSQL → Kafka)
2. ✅ Flink job for stream processing
3. ✅ Schema Registry integration
4. ✅ Flink checkpoints (exactly-once)
5. ✅ Watermark for late data
6. ✅ Stream write to MinIO (Parquet)

**Deliverables:**
- Kafka Connect CDC pipeline
- Flink streaming job
- Checkpoint configuration
- Late data handling

---

### Phase 4: Backfill Integration (Week 7-8)

**Goals:** Unified backfill for batch + streaming

**Tasks:**
1. ✅ Batch backfill command/script
2. ✅ Streaming offset replay script
3. ✅ Hybrid approach (batch history + stream current)
4. ✅ Idempotency verification
5. ✅ Backfill monitoring + logging
6. ✅ Documentation + runbook

**Deliverables:**
- Backfill CLI tool
- Offset management utility
- Backfill runbook
- Testing suite

---

### Phase 5: Production Hardening (Week 9-10)

**Goals:** Observability, monitoring, production-ready

**Tasks:**
1. ✅ Metrics collection (data volume, latency)
2. ✅ Alerting (Slack, email)
3. ✅ Dashboard (Grafana)
4. ✅ Log aggregation
5. ✅ Performance tuning
6. ✅ Chaos testing (failure scenarios)

**Deliverables:**
- Monitoring dashboard
- Alerting rules
- Performance benchmarks
- Failure recovery tests

---

## Project Structure

```
backfill-pipeline-project/
├── docker-compose.yml              # All services
├── docker/
│   ├── airflow/
│   │   ├── Dockerfile
│   │   ├── dags/
│   │   │   ├── clickstream_batch_dag.py
│   │   │   └── clickstream_backfill_dag.py
│   │   └── scripts/
│   ├── spark/
│   │   ├── Dockerfile
│   │   └── jobs/
│   │       ├── bronze_clicks.py
│   │       ├── silver_clicks.py
│   │       └── gold_metrics.py
│   ├── flink/
│   │   ├── Dockerfile
│   │   └── jobs/
│   │       └── ClickStreamJob.java
│   └── kafka/
│       └── connect/
│           └── postgres-cdc.json
├── src/
│   ├── batch/
│   │   ├── extract.py
│   │   ├── transform.py
│   │   └── load.py
│   ├── streaming/
│   │   └── flink/
│   ├── quality/
│   │   └── expectations.py
│   └── utils/
│       ├── schema.py
│       └── idempotency.py
├── tests/
│   ├── test_batch_pipeline.py
│   ├── test_streaming_pipeline.py
│   └── test_backfill.py
├── docs/
│   ├── architecture.md
│   ├── backfill-runbook.md
│   └── troubleshooting.md
├── scripts/
│   ├── backfill-batch.sh
│   ├── backfill-streaming.sh
│   └── reset-offsets.sh
├── config/
│   ├── application.yml
│   └── flink-conf.yaml
└── README.md
```

---

## Key Implementation Details

### Idempotent Writes (Batch)

```python
# Spark batch write with idempotency using partition overwrite
def write_idempotent(df, table, partition_col, batch_id):
    """
    Idempotent write: overwrite specific partition
    Safe to re-run with same batch_id
    
    Requires Delta Lake or Hive partitioning
    """
    # Overwrite partition atomically
    df.write \
        .mode("overwrite") \
        .partitionBy(partition_col) \
        .option("overwritePartition", "true") \
        .insertInto(table)
    
    # Log batch completion
    log_batch_complete(batch_id, table)
```

---

### Exactly-Once Semantics (Flink)

```java
// Flink configuration for exactly-once (Flink 1.19+)
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

// Enable checkpointing (every 5 minutes)
env.configureCheckpointing()
    .interval(5 * 60 * 1000)
    .checkpointingMode(CheckpointingMode.EXACTLY_ONCE);

// State backend (for checkpoints)
env.setStateBackend(new RocksDBStateBackend("hdfs://namenode:9000/flink-checkpoints"));

// Kafka source with exactly-once
FlinkKafkaConsumer<Click> consumer = new FlinkKafkaConsumer<>(
    "clicks",
    new KafkaClickSchema(),
    properties
);
consumer.setCommitOffsetsOnCheckpoints(true);  // Exactly-once
```

---

### Schema Evolution Handling

```python
# Spark schema evolution
def read_with_evolution(path):
    """
    Auto-merge new columns from schema evolution
    """
    return spark.read \
        .option("mergeSchema", "true") \
        .parquet(path)

# Schema validation with type checking
def validate_schema(df, expected_schema):
    """
    Check if DataFrame schema matches expected
    Alert on breaking changes
    
    expected_schema: dict of {column_name: spark_type}
    e.g., {"click_id": LongType(), "user_id": LongType()}
    """
    from pyspark.sql.types import DataType
    
    current_schema = {field.name: field.dataType for field in df.schema}
    
    # New columns (OK - backward compatible)
    new_cols = set(current_schema.keys()) - set(expected_schema.keys())
    if new_cols:
        logger.warning(f"New columns detected: {new_cols}")
    
    # Missing columns (BREAKING)
    missing_cols = set(expected_schema.keys()) - set(current_schema.keys())
    if missing_cols:
        raise SchemaValidationError(f"Missing columns: {missing_cols}")
    
    # Type mismatches (BREAKING)
    for col_name, expected_type in expected_schema.items():
        if col_name in current_schema:
            if not isinstance(current_schema[col_name], type(expected_type)):
                raise SchemaValidationError(
                    f"Type mismatch for {col_name}: "
                    f"expected {expected_type}, got {current_schema[col_name]}"
                )
```

---

### Data Quality Testing (Great Expectations)

```python
from great_expectations.dataset import SparkDFDataset

def validate_clicks(df):
    """
    Run data quality checks on clicks data
    """
    # Convert Spark DataFrame to GE dataset
    ge_df = SparkDFDataset(df)
    
    # Define expectations
    ge_df.expect_column_to_exist("click_id")
    ge_df.expect_column_to_exist("user_id")
    ge_df.expect_column_values_to_not_be_null("click_id")
    ge_df.expect_column_values_to_not_be_null("user_id")
    ge_df.expect_column_values_to_be_unique("click_id")
    ge_df.expect_column_values_to_be_between("user_id", min_value=0)
    ge_df.expect_column_values_to_be_in_set("event_type", 
        ["page_view", "click", "scroll", "purchase"])
    
    # Validate
    result = ge_df.validate()
    
    if result["success"]:
        logger.info("All DQ checks passed")
        return True
    else:
        logger.error("DQ checks failed")
        send_alert(f"DQ failure: {result['results']}")
        return False
```

---

## Backfill Commands

### Batch Backfill Script

```bash
#!/bin/bash
set -euo pipefail

# scripts/backfill-batch.sh

DAG_ID="clickstream_batch_dag"
START_DATE="${1:-}"
END_DATE="${2:-}"

if [ -z "$START_DATE" ] || [ -z "$END_DATE" ]; then
    echo "Usage: $0 <start_date> <end_date>"
    echo "Example: $0 2024-01-01 2024-03-20"
    exit 1
fi

echo "Starting batch backfill from $START_DATE to $END_DATE"

# Airflow backfill
if ! airflow dags backfill "$DAG_ID" \
    -s "$START_DATE" \
    -e "$END_DATE" \
    --rerun-failed \
    --local; then
    echo "ERROR: Airflow backfill failed"
    exit 1
fi

# Verify backfill
if ! python scripts/verify-backfill.py --start-date "$START_DATE" --end-date "$END_DATE"; then
    echo "ERROR: Backfill verification failed"
    exit 1
fi

echo "Batch backfill complete"
```

---

### Streaming Offset Replay

```bash
#!/bin/bash
# scripts/backfill-streaming.sh

TOPIC="clicks"
CONSUMER_GROUP="flink-consumer"
RESET_MODE=$1  # 'earliest' or 'latest' or 'offset'

if [ -z "$RESET_MODE" ]; then
    echo "Usage: $0 <earliest|latest|offset>"
    exit 1
fi

echo "Stopping Flink job..."
# Stop Flink job (graceful savepoint)
flink cancel --with-savepoint <job_id>

echo "Resetting Kafka offsets..."
# Reset consumer group offset
kafka-consumer-groups \
    --bootstrap localhost:9092 \
    --group $CONSUMER_GROUP \
    --topic $TOPIC \
    --reset-to-$RESET_MODE \
    --execute

echo "Restarting Flink job..."
# Restart Flink from savepoint
flink run -s <savepoint_path> flink-job.jar

echo "Streaming backfill complete"
```

---

## Monitoring & Alerting

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Batch Pipeline Duration** | < 2 hours | > 4 hours |
| **Streaming Lag** | < 1 minute | > 5 minutes |
| **Data Freshness** | < 1 hour | > 4 hours |
| **DQ Test Pass Rate** | 100% | < 95% |
| **Backfill Success Rate** | 100% | Any failure |

---

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: data_pipeline
    rules:
      - alert: PipelineFailure
        expr: pipeline_status == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pipeline {{ pipeline_name }} failed"
          
      - alert: StreamingLagHigh
        expr: kafka_consumer_lag > 300000  # 5 minutes
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Streaming lag is {{ $value }}ms"
          
      - alert: BackfillIncomplete
        expr: backfill_progress < 100
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Backfill {{ backfill_id }} incomplete"
```

---

## Testing Strategy

### Unit Tests

```python
def test_idempotent_write():
    """Test that writing same batch twice produces same result"""
    batch_id = "test-batch-1"
    
    # First write
    write_idempotent(df1, "clicks", "batch_id", batch_id)
    count1 = spark.table("clicks").count()
    
    # Second write (same batch_id)
    write_idempotent(df2, "clicks", "batch_id", batch_id)
    count2 = spark.table("clicks").count()
    
    assert count1 == count2, "Idempotent write failed"
```

### Integration Tests

```python
def test_backfill_end_to_end():
    """Test complete backfill flow"""
    # Generate test data
    generate_test_data(start_date="2024-01-01", end_date="2024-01-10")
    
    # Run backfill
    run_backfill(start_date="2024-01-01", end_date="2024-01-10")
    
    # Verify results
    verify_data_completeness()
    verify_data_quality()
    verify_idempotency()
```

### Chaos Tests

```python
def test_pipeline_recovery():
    """Test pipeline recovers from failure"""
    # Start pipeline
    start_pipeline()
    
    # Simulate failure (kill worker)
    kill_worker()
    
    # Wait for retry
    wait_for_retry()
    
    # Verify completion
    assert pipeline_completed_successfully()
```

---

## Success Criteria

| Criterion | Definition |
|-----------|------------|
| **Functional** | Batch + streaming pipelines process data correctly |
| **Idempotent** | Re-runs produce identical results |
| **Backfillable** | Can backfill any date range on demand |
| **Schema Evolution** | Handles new columns without breaking |
| **Data Quality** | All DQ tests pass consistently |
| **Observability** | Metrics, logs, alerts working |
| **Documentation** | Runbook, architecture docs complete |

---

## Next Steps

1. **Review this plan** - Confirm architecture and scope
2. **Set up infrastructure** - Docker Compose for all services
3. **Implement Phase 1** - Foundation (batch extract → bronze)
4. **Iterate through phases** - Build incrementally
5. **Test thoroughly** - Unit, integration, chaos tests
6. **Document everything** - Runbook, troubleshooting guide

---

## Questions for You

Before we start implementing, I need to know:

1. **Docker vs Local?** - Run all services in Docker, or some locally?
2. **Language preference?** - Spark (Python/Scala), Flink (Java/Scala)?
3. **Kafka Connect?** - Use Debezium for CDC, or custom extract?
4. **Sample data?** - Generate synthetic clickstream data, or use real dataset?
5. **Timeline?** - Want to complete in 2 weeks, 4 weeks, or 8 weeks?

Let me know and we'll start building!
