# Implementation Plan - Clickstream Analytics Pipeline

## Project Context
**Practice project for interview preparation**
- All services in Docker
- Spark using Python (PySpark)
- Debezium for CDC
- Synthetic data using Faker library
- No fixed timeline - complete ASAP
- **Streaming: Spark Structured Streaming (no Flink)**

---

## Phase 1: Foundation Setup

### Goal
Get all infrastructure running with sample data and basic batch extraction

### Tasks

#### 1.1 Docker Infrastructure
- [ ] Verify docker-compose.yml has all services
- [ ] Build and start all containers
- [ ] Verify health checks pass
- [ ] Document service URLs and credentials

**Services to verify:**
| Service | Port | Health Check |
|---------|------|--------------|
| PostgreSQL | 5432 | pg_isready |
| MinIO | 9000/9001 | /minio/health/live |
| Kafka | 29092 | kafka-broker-api-versions |
| Schema Registry | 8081 | HTTP 200 |
| Kafka Connect | 8083 | /connector-plugins |
| Airflow | 8080 | /health |
| Spark Master | 8081/7077 | Web UI |
| Redis | 6379 | redis-cli ping |

**Commands:**
```bash
# Build and start
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

#### 1.2 PostgreSQL Setup
- [ ] Create init.sql with schema (clicks, sessions tables)
- [ ] Add indexes for CDC (updated_at, event_timestamp)
- [ ] Generate synthetic data using Faker (100K+ records)
- [ ] Verify data count

**Schema:**
```sql
-- clicks table
-- sessions table
-- indexes on updated_at, event_timestamp
```

**Data Generation Script:**
```python
# scripts/generate_sample_data.py
from faker import Faker
import psycopg2
from datetime import datetime, timedelta

# Generate 100K click events
# Generate 10K sessions
# Date range: 2024-01-01 to 2024-03-21
```

---

#### 1.3 MinIO Setup
- [ ] Create buckets: clickstream-bronze, clickstream-silver, clickstream-gold
- [ ] Configure bucket policies
- [ ] Verify access via mc client

**Commands:**
```bash
docker-compose exec minio mc alias set myminio http://minio:9000 minioadmin minioadmin123
docker-compose exec minio mc mb myminio/clickstream-bronze
docker-compose exec minio mc mb myminio/clickstream-silver
docker-compose exec minio mc mb myminio/clickstream-gold
```

---

#### 1.4 Basic Airflow DAG
- [ ] Create clickstream_batch_dag.py
- [ ] Implement extract_clicks task (PostgreSQL → Spark)
- [ ] Implement write_bronze task (Spark → MinIO Parquet)
- [ ] Configure daily schedule
- [ ] Test manual trigger

**DAG Structure:**
```
extract_clicks → write_bronze
     ↓              ↓
  PostgreSQL    MinIO Bronze
```

---

#### 1.5 Spark Batch Job
- [ ] Create bronze_clicks.py
- [ ] Read from PostgreSQL via JDBC
- [ ] Write to MinIO as Parquet
- [ ] Implement partitioning by extract_date
- [ ] Test idempotent write

**Code Location:**
```
src/batch/bronze_clicks.py
```

---

### Deliverables
1. ✅ All Docker services running
2. ✅ PostgreSQL with 100K+ synthetic click records
3. ✅ MinIO buckets created
4. ✅ Airflow DAG visible in UI
5. ✅ Spark job writes to bronze layer

### Definition of Done
- [ ] `docker-compose ps` shows all services healthy
- [ ] PostgreSQL has clicks and sessions tables with data
- [ ] MinIO shows 3 buckets
- [ ] Airflow DAG can be triggered manually
- [ ] Bronze layer Parquet files visible in MinIO

---

## Phase 2: Complete Batch Pipeline

### Goal
Full batch pipeline with transformations, data quality, and backfill capability

### Tasks

#### 2.1 Silver Layer Transformations
- [ ] Create silver_clicks.py Spark job
- [ ] Clean data (handle nulls, deduplicate)
- [ ] Enrich (add domain from URL, device type from user agent)
- [ ] Validate schema
- [ ] Write to MinIO silver partitioned by event_date

**Transformations:**
```python
# Clean
- Remove duplicates on click_id
- Fill null user_agent with 'unknown'
- Validate event_type in allowed set

# Enrich
- Extract domain from page_url
- Parse device_type from user_agent
- Add traffic_source from referrer
```

---

#### 2.2 Gold Layer Aggregations
- [ ] Create gold_metrics.py Spark job
- [ ] Aggregate daily_metrics (count by date, event_type)
- [ ] Aggregate user_sessions (sessions per user)
- [ ] Write partitioned by date/user_id

**Aggregations:**
```python
# daily_metrics
- date
- event_type
- count_events
- unique_users
- avg_session_duration

# user_sessions
- user_id
- session_count
- total_page_views
- bounce_rate
```

---

#### 2.3 Great Expectations Integration
- [ ] Create expectations.py
- [ ] Define click expectations (not null, unique, valid event_type)
- [ ] Integrate with Airflow DAG
- [ ] Fail pipeline on DQ violations
- [ ] Generate DQ reports

**Expectations:**
```python
expect_column_values_to_not_be_null('click_id')
expect_column_values_to_be_unique('click_id')
expect_column_values_to_be_in_set('event_type', [...])
expect_column_values_to_be_between('user_id', min_value=0)
```

---

#### 2.4 Schema Evolution Handling
- [ ] Create utils/schema.py
- [ ] Implement mergeSchema option
- [ ] Add schema validation function
- [ ] Log warnings on new columns
- [ ] Raise errors on breaking changes

---

#### 2.5 Backfill Implementation
- [ ] Create scripts/backfill-batch.sh
- [ ] Accept start_date and end_date parameters
- [ ] Call Airflow backfill command
- [ ] Add verification step
- [ ] Test with date range

**Script:**
```bash
#!/bin/bash
airflow dags backfill clickstream_batch_dag -s $START_DATE -e $END_DATE
python scripts/verify-backfill.py --start-date $START_DATE --end-date $END_DATE
```

---

#### 2.6 Error Handling & Alerting
- [ ] Add retry logic to Airflow tasks (retries=3)
- [ ] Configure exponential backoff
- [ ] Add Slack webhook (optional)
- [ ] Log errors to file
- [ ] Create alert email template

---

### Deliverables
1. ✅ Silver layer with cleaned/enriched data
2. ✅ Gold layer with aggregations
3. ✅ DQ tests running in pipeline
4. ✅ Backfill script working
5. ✅ Error handling with retries

### Definition of Done
- [ ] Bronze → Silver → Gold pipeline runs end-to-end
- [ ] DQ tests pass or fail appropriately
- [ ] Backfill script processes date range successfully
- [ ] Re-run produces same results (idempotent)
- [ ] Failed tasks retry automatically

---

## Phase 3: Streaming Pipeline (Spark Structured Streaming)

### Goal
Real-time ingestion using Spark Structured Streaming with Kafka Connect (Debezium)

### Tasks

#### 3.1 Debezium PostgreSQL Connector
- [ ] Create docker/kafka/connect/postgres-cdc.json
- [ ] Configure connector properties
- [ ] Register connector via Kafka Connect REST API
- [ ] Verify connector running
- [ ] Check Kafka topic created

**Connector Config:**
```json
{
  "name": "postgres-cdc-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "admin",
    "database.password": "admin123",
    "database.dbname": "clickstream",
    "topic.prefix": "dbserver1",
    "schema.include.list": "public",
    "table.include.list": "public.clicks,public.sessions",
    "plugin.name": "pgoutput",
    "slot.name": "debezium"
  }
}
```

---

#### 3.2 Kafka Topic Verification
- [ ] List topics (clicks, sessions)
- [ ] Verify message flow
- [ ] Check partition count
- [ ] Test consuming messages

**Commands:**
```bash
kafka-topics --bootstrap-server kafka:9092 --list
kafka-console-consumer --bootstrap-server kafka:9092 --topic dbserver1.public.clicks
```

---

#### 3.3 Spark Structured Streaming Job
- [ ] Create streaming_clicks.py
- [ ] Read from Kafka topic
- [ ] Parse JSON schema
- [ ] Apply watermarks for late data
- [ ] Write to MinIO (Parquet, streaming)

**Spark Streaming Code:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, watermark

spark = SparkSession.builder.appName("clickstream-streaming").getOrCreate()

# Read from Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.clicks") \
    .option("startingOffsets", "earliest") \
    .load()

# Parse JSON
schema = ... # Define schema
df_parsed = df.select(from_json(col("value").cast("string"), schema).alias("data"))
df_flat = df_parsed.select("data.*")

# Add watermark (10 minutes late data)
df_watermarked = df_flat.withWatermark("event_timestamp", "10 minutes")

# Write to MinIO
query = df_watermarked.writeStream \
    .format("parquet") \
    .option("path", "s3a://clickstream-silver/streaming/clicks/") \
    .option("checkpointLocation", "s3a://clickstream-silver/checkpoints/") \
    .partitionBy("event_date") \
    .trigger(processingTime='1 minute') \
    .start()

query.awaitTermination()
```

---

#### 3.4 Schema Registry Integration
- [ ] Configure Spark to use Schema Registry
- [ ] Register Avro schema
- [ ] Enable schema evolution
- [ ] Test schema compatibility

---

#### 3.5 Checkpointing Configuration
- [ ] Configure Spark checkpointing
- [ ] Set checkpoint location (MinIO)
- [ ] Test recovery from checkpoint
- [ ] Verify exactly-once semantics

---

#### 3.6 Late Data Handling
- [ ] Configure watermark (10 minutes)
- [ ] Test late event arrival
- [ ] Verify late data included
- [ ] Document late data strategy

---

### Deliverables
1. ✅ Debezium connector streaming CDC events
2. ✅ Spark Structured Streaming job processing
3. ✅ Checkpoints working
4. ✅ Watermarks handling late data
5. ✅ Streaming writes to MinIO

### Definition of Done
- [ ] New PostgreSQL inserts appear in Kafka within seconds
- [ ] Spark Streaming consumes and processes events
- [ ] Checkpoints created in MinIO
- [ ] Late events (within watermark) are processed
- [ ] MinIO streaming/ folder has Parquet files

---

## Phase 4: Backfill Integration

### Goal
Unified backfill for batch + streaming with hybrid approach

### Tasks

#### 4.1 Batch Backfill Script
- [ ] Finalize scripts/backfill-batch.sh
- [ ] Add error handling (set -e)
- [ ] Add logging
- [ ] Add progress output
- [ ] Test with various date ranges

---

#### 4.2 Streaming Offset Replay
- [ ] Create scripts/backfill-streaming.sh
- [ ] Stop Spark Streaming job
- [ ] Reset Kafka consumer group offset
- [ ] Restart Spark Streaming
- [ ] Verify offset reset

**Commands:**
```bash
# Reset to earliest
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group spark-consumer --topic clicks --reset-to-earliest --execute
```

---

#### 4.3 Hybrid Approach
- [ ] Document strategy: batch for history + stream for current
- [ ] Create scripts/backfill-hybrid.sh
- [ ] Run batch backfill for old data
- [ ] Switch to streaming for new data
- [ ] Verify no duplicates

---

#### 4.4 Idempotency Verification
- [ ] Create test_idempotency.py
- [ ] Run backfill twice
- [ ] Compare record counts
- [ ] Compare data checksums
- [ ] Assert identical results

---

#### 4.5 Backfill Monitoring
- [ ] Add logging to backfill scripts
- [ ] Track progress (records processed)
- [ ] Track duration
- [ ] Output summary at end
- [ ] Log to file for audit

---

#### 4.6 Documentation & Runbook
- [ ] Create docs/backfill-runbook.md
- [ ] Document batch backfill steps
- [ ] Document streaming backfill steps
- [ ] Document hybrid approach
- [ ] Add troubleshooting section
- [ ] Add FAQ

---

### Deliverables
1. ✅ Batch backfill script
2. ✅ Streaming offset replay script
3. ✅ Hybrid backfill script
4. ✅ Idempotency tests
5. ✅ Backfill runbook

### Definition of Done
- [ ] All backfill scripts executable and tested
- [ ] Running backfill twice produces same result
- [ ] Runbook documents all scenarios
- [ ] Monitoring shows progress during backfill

---

## Phase 5: Production Hardening

### Goal
Observability, monitoring, and production-ready features

### Tasks

#### 5.1 Metrics Collection
- [ ] Instrument batch pipeline (record count, duration)
- [ ] Instrument streaming pipeline (lag, throughput)
- [ ] Export metrics to Prometheus (optional)
- [ ] Create metrics dashboard query

**Metrics:**
- records_processed
- pipeline_duration_seconds
- kafka_consumer_lag
- data_freshness_minutes

---

#### 5.2 Alerting
- [ ] Configure Airflow email alerts
- [ ] Set up Slack webhook (optional)
- [ ] Create alert rules for failures
- [ ] Test alert triggers
- [ ] Document alert response

---

#### 5.3 Dashboard
- [ ] Create Grafana dashboard (optional)
- [ ] Or use Airflow UI
- [ ] Show pipeline status
- [ ] Show data volume
- [ ] Show latency

---

#### 5.4 Log Aggregation
- [ ] Configure log paths
- [ ] Centralize logs (optional: ELK)
- [ ] Add structured logging
- [ ] Include job_id, batch_id in logs

---

#### 5.5 Performance Tuning
- [ ] Benchmark batch pipeline
- [ ] Tune Spark parallelism
- [ ] Tune streaming parallelism
- [ ] Document performance characteristics
- [ ] Identify bottlenecks

---

#### 5.6 Chaos Testing
- [ ] Kill worker during pipeline
- [ ] Simulate Kafka outage
- [ ] Simulate MinIO outage
- [ ] Verify recovery
- [ ] Document failure scenarios

---

### Deliverables
1. ✅ Metrics collection working
2. ✅ Alerts configured
3. ✅ Dashboard visible
4. ✅ Logs centralized
5. ✅ Performance benchmarks
6. ✅ Chaos tests passing

### Definition of Done
- [ ] Pipeline failure triggers alert
- [ ] Dashboard shows real-time status
- [ ] Logs searchable
- [ ] Performance meets targets
- [ ] System recovers from failures

---

## Testing Strategy

### Unit Tests
```python
# tests/test_batch_pipeline.py
def test_idempotent_write()
def test_schema_evolution()
def test_dq_validation()
```

### Integration Tests
```python
# tests/test_integration.py
def test_backfill_end_to_end()
def test_streaming_pipeline()
```

### Chaos Tests
```python
# tests/test_chaos.py
def test_pipeline_recovery()
def test_kafka_outage_handling()
```

---

## Project Structure (Final)

```
backfill-pipeline-project/
├── docker-compose.yml
├── .env
├── PROJECT_PLAN.md
├── IMPLEMENTATION_PLAN.md
├── docker/
│   ├── airflow/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── dags/
│   │   │   ├── clickstream_batch_dag.py
│   │   │   └── clickstream_backfill_dag.py
│   │   ├── scripts/
│   │   └── logs/
│   ├── spark/
│   │   ├── Dockerfile
│   │   └── jobs/
│   ├── kafka/
│   │   └── connect/
│   │       └── postgres-cdc.json
│   └── postgres/
│       └── init.sql
├── src/
│   ├── batch/
│   │   ├── bronze_clicks.py
│   │   ├── silver_clicks.py
│   │   └── gold_metrics.py
│   ├── streaming/
│   │   └── streaming_clicks.py
│   ├── quality/
│   │   └── expectations.py
│   └── utils/
│       ├── schema.py
│       └── idempotency.py
├── scripts/
│   ├── generate_sample_data.py
│   ├── backfill-batch.sh
│   ├── backfill-streaming.sh
│   ├── backfill-hybrid.sh
│   ├── verify-backfill.py
│   └── setup-minio.sh
├── tests/
│   ├── test_batch_pipeline.py
│   ├── test_streaming_pipeline.py
│   ├── test_backfill.py
│   └── test_idempotency.py
├── docs/
│   ├── architecture.md
│   ├── backfill-runbook.md
│   └── troubleshooting.md
└── .planning/
    └── phase-plans/
```

---

## Quick Reference Commands

### Docker Management
```bash
# Start all
docker-compose up -d --build

# Stop all
docker-compose down

# View logs
docker-compose logs -f <service>

# Restart service
docker-compose restart <service>

# Rebuild
docker-compose up -d --build --force-recreate
```

### Airflow Commands
```bash
# List DAGs
airflow dags list

# Trigger DAG
airflow dags trigger clickstream_batch_dag

# Backfill
airflow dags backfill -s 2024-01-01 -e 2024-03-20 clickstream_batch_dag
```

### Kafka Commands
```bash
# List topics
kafka-topics --bootstrap-server kafka:9092 --list

# Describe topic
kafka-topics --bootstrap-server kafka:9092 --describe --topic clicks

# Reset offset
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group spark-consumer --topic clicks --reset-to-earliest --execute
```

### MinIO Commands
```bash
# List buckets
mc ls myminio

# Upload file
mc cp file.parquet myminio/clickstream-bronze/

# Remove bucket
mc rm --recursive --force myminio/clickstream-bronze/
```

### Spark Commands
```bash
# Submit batch job
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark/jobs/bronze_clicks.py

# Check Spark UI
open http://localhost:8081
```

---

## Environment Variables

```bash
# View .env file
cat .env

# Set MinIO credentials
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin123
export AWS_ENDPOINT_URL=http://localhost:9000
```

---

## Health Checks

```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U admin

# MinIO
curl http://localhost:9000/minio/health/live

# Kafka
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Schema Registry
curl http://localhost:8081/subjects

# Kafka Connect
curl http://localhost:8083/connector-plugins

# Airflow
curl http://localhost:8080/health

# Spark Master
curl http://localhost:8081

# Redis
docker-compose exec redis redis-cli ping
```

---

## Common Issues & Fixes

### PostgreSQL Connection Refused
```bash
# Check if running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

### MinIO Bucket Not Found
```bash
# Create bucket
docker-compose exec minio mc mb myminio/clickstream-bronze
```

### Kafka Connect Plugin Not Found
```bash
# Check plugins
curl http://localhost:8083/connector-plugins

# Rebuild Kafka Connect
docker-compose up -d --build kafka-connect
```

### Airflow DAG Not Visible
```bash
# Check DAGs folder
docker-compose exec airflow-webserver ls /opt/airflow/dags

# Trigger refresh
touch docker/airflow/dags/clickstream_batch_dag.py
```

### Spark Job Failed
```bash
# Check logs
docker-compose logs spark-master
docker-compose logs spark-worker

# Increase memory
export SPARK_WORKER_MEMORY=4G
docker-compose up -d --build spark-worker
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| Spark Master | http://localhost:8081 | - |
| Schema Registry | http://localhost:8081 | - |
| Kafka Connect | http://localhost:8083 | - |
| PostgreSQL | localhost:5432 | admin / admin123 |
| Kafka (host) | localhost:29092 | - |
| Redis | localhost:6379 | - |
