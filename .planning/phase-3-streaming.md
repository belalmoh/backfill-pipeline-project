# Phase 3: Streaming Pipeline (Spark Structured Streaming) - Detailed Plan

## Status: Not Started
## Estimated Duration: 3-4 days
## Priority: Medium (after Phase 2)

---

## Goals
1. Debezium PostgreSQL connector streaming CDC
2. Spark Structured Streaming job processing
3. Schema Registry integration
4. Checkpoints working (exactly-once)
5. Watermarks handling late data
6. Streaming writes to MinIO

---

## Task Breakdown

### 3.1 Debezium PostgreSQL Connector
**Status:** Pending
**Files:** `docker/kafka/connect/postgres-cdc.json`

**Steps:**
1. Create connector config
2. Register via REST API
3. Verify connector running
4. Check Kafka topic created
5. Test message flow

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
    "slot.name": "debezium",
    "publication.name": "debezium_publication",
    "slot.retain.temp.interval": "10m",
    "tombstones.on.delete": "true",
    "include.schema.changes": "true"
  }
}
```

**Register:**
```bash
curl -X POST -H "Content-Type: application/json" \
  --data @docker/kafka/connect/postgres-cdc.json \
  http://localhost:8083/connectors | jq
```

**Verify:**
```bash
# Check status
curl http://localhost:8083/connectors/postgres-cdc-connector/status | jq

# Check topics
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 --list

# Consume messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic dbserver1.public.clicks --from-beginning
```

**Acceptance Criteria:**
- [ ] Connector registered
- [ ] Status shows RUNNING
- [ ] Kafka topics created (dbserver1.public.clicks)
- [ ] Messages flowing to Kafka
- [ ] Schema changes included

---

### 3.2 Kafka Topic Verification
**Status:** Pending
**Files:** `scripts/verify-kafka.sh`

**Steps:**
1. List topics
2. Describe topic (partitions, retention)
3. Check message count
4. Verify partition distribution
5. Test consuming

**Commands:**
```bash
# List topics
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 --list

# Describe
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 \
  --describe --topic dbserver1.public.clicks

# Count messages
docker-compose exec kafka kafka-run-class \
  kafka.tools.GetOffsetShell \
  --broker-list kafka:9092 \
  --topic dbserver1.public.clicks
```

**Acceptance Criteria:**
- [ ] Topic exists
- [ ] Partitions configured (1-3)
- [ ] Replication factor 1 (dev)
- [ ] Messages present
- [ ] Consumer can read

---

### 3.3 Spark Structured Streaming Job
**Status:** Pending
**Files:** `src/streaming/streaming_clicks.py`

**Steps:**
1. Create Spark Streaming job
2. Read from Kafka
3. Parse JSON schema
4. Apply watermarks
5. Write to MinIO

**PySpark Streaming Code:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, watermark
from pyspark.sql.types import StructType, StructField, LongType, StringType, TimestampType

spark = SparkSession.builder \
    .appName("clickstream-streaming") \
    .getOrCreate()

# Define schema
schema = StructType([
    StructField("click_id", LongType()),
    StructField("user_id", LongType()),
    StructField("session_id", StringType()),
    StructField("page_url", StringType()),
    StructField("event_type", StringType()),
    StructField("event_timestamp", TimestampType()),
    StructField("user_agent", StringType()),
    StructField("ip_address", StringType()),
    StructField("referrer_url", StringType()),
    StructField("created_at", TimestampType()),
    StructField("updated_at", TimestampType())
])

# Read from Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.clicks") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load()

# Parse JSON (Debezium format)
debezium_schema = StructType([
    StructField("payload", schema),
    StructField("schema", StringType()),
    StructField("op", StringType()),
    StructField("ts_ms", LongType())
])

df_parsed = df.select(from_json(col("value").cast("string"), debezium_schema).alias("data"))
df_flat = df_parsed.select("data.payload.*")

# Add watermark (10 minutes late data)
df_watermarked = df_flat.withWatermark("event_timestamp", "10 minutes")

# Add processing date for partitioning
from pyspark.sql.functions import current_date
df_with_date = df_watermarked.withColumn("event_date", current_date())

# Write to MinIO (streaming file sink)
query = df_with_date.writeStream \
    .format("parquet") \
    .option("path", "s3a://clickstream-silver/streaming/clicks/") \
    .option("checkpointLocation", "s3a://clickstream-silver/checkpoints/streaming/") \
    .partitionBy("event_date") \
    .trigger(processingTime='1 minute') \
    .outputMode("append") \
    .start()

query.awaitTermination()
```

**Acceptance Criteria:**
- [ ] Job compiles
- [ ] Job runs
- [ ] Consumes from Kafka
- [ ] Applies watermark
- [ ] Writes to MinIO
- [ ] Checkpoints created

---

### 3.4 Schema Registry Integration
**Status:** Pending
**Files:** `src/streaming/schema.py`

**Steps:**
1. Register Avro schema
2. Configure Spark to use registry
3. Enable schema evolution
4. Test compatibility

**Schema Registration:**
```python
import requests

schema = {
    "type": "record",
    "name": "Click",
    "fields": [
        {"name": "click_id", "type": "long"},
        {"name": "user_id", "type": "long"},
        {"name": "event_timestamp", "type": "string"},
        {"name": "event_type", "type": "string"}
    ]
}

# Register
response = requests.post(
    "http://localhost:8081/subjects/clicks-value",
    json={"schema": json.dumps(schema)},
    headers={"Content-Type": "application/json"}
)

print(response.json())
```

**Acceptance Criteria:**
- [ ] Schema registered
- [ ] Spark uses schema
- [ ] Evolution enabled
- [ ] Compatible schemas accepted

---

### 3.5 Checkpointing Configuration
**Status:** Pending
**Files:** `config/spark-conf.yaml`

**Steps:**
1. Configure checkpointing
2. Set checkpoint location (MinIO)
3. Test recovery from checkpoint
4. Verify exactly-once semantics

**Configuration:**
```python
# In streaming job
query = df.writeStream \
    .format("parquet") \
    .option("checkpointLocation", "s3a://clickstream-silver/checkpoints/streaming/") \
    .start()
```

**Test Recovery:**
```bash
# Stop streaming job (Ctrl+C)
# Check checkpoint exists
mc ls myminio/clickstream-silver/checkpoints/

# Restart job (reads from checkpoint)
spark-submit src/streaming/streaming_clicks.py

# Verify continues from checkpoint
# (no duplicates, no data loss)
```

**Acceptance Criteria:**
- [ ] Checkpoints created in MinIO
- [ ] Recovery from checkpoint works
- [ ] No data loss on recovery
- [ ] No duplicates on recovery

---

### 3.6 Late Data Handling
**Status:** Pending
**Files:** `src/streaming/streaming_clicks.py`

**Steps:**
1. Configure watermark (10 min)
2. Test late event arrival
3. Verify late data included
4. Document strategy

**Watermark:**
```python
df_watermarked = df_flat.withWatermark("event_timestamp", "10 minutes")
```

**Test:**
```python
# Insert late event (5 min old)
insert_event(timestamp=now() - timedelta(minutes=5))

# Verify processed
check_minio_for_late_event()
```

**Acceptance Criteria:**
- [ ] Watermark configured
- [ ] Late events (within 10 min) processed
- [ ] Very late events (>10 min) handled
- [ ] Documented behavior

---

## Dependencies

```
1.3 MinIO Setup (Phase 1)
    ↓
3.1 Debezium Connector
    ↓
3.2 Kafka Topics
    ↓
3.3 Spark Streaming Job
    ↓
3.4 Schema Registry
    ↓
3.5 Checkpoints
    ↓
3.6 Late Data
```

---

## Testing Strategy

### Manual Tests
```bash
# Test connector
curl http://localhost:8083/connectors/postgres-cdc-connector/status

# Test Kafka flow
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic dbserver1.public.clicks

# Test Spark Streaming job
docker-compose exec spark-master spark-submit \
  /opt/spark/jobs/streaming_clicks.py

# Test late data
# Insert event with old timestamp
# Verify processed
```

### Automated Tests
```python
# tests/test_phase3.py
def test_cdc_connector_running():
    status = get_connector_status()
    assert status == "RUNNING"

def test_kafka_messages_flowing():
    count = count_kafka_messages()
    assert count > 0

def test_spark_streaming_runs():
    result = run_spark_streaming()
    assert result.exit_code == 0

def test_checkpoints_created():
    checkpoints = list_checkpoints()
    assert len(checkpoints) > 0

def test_late_data_handled():
    insert_late_event()
    assert event_processed()
```

---

## Deliverables Checklist

- [ ] `docker/kafka/connect/postgres-cdc.json` - Connector config
- [ ] `src/streaming/streaming_clicks.py` - Spark Streaming job
- [ ] `src/streaming/schema.py` - Schema utilities
- [ ] `config/spark-conf.yaml` - Spark config
- [ ] `tests/test_phase3.py` - Phase 3 tests

---

## Definition of Done

### Functional
- [ ] Debezium connector streaming CDC events
- [ ] Spark Streaming job processing stream
- [ ] Checkpoints created in MinIO
- [ ] Watermarks handle late data
- [ ] MinIO streaming/ has Parquet files

### Documentation
- [ ] Phase 3 README updated
- [ ] CDC flow documented
- [ ] Spark Streaming job documented
- [ ] Late data strategy documented

### Code Quality
- [ ] Code commented
- [ ] Error handling
- [ ] Logs informative
- [ ] Exactly-once semantics

---

## Troubleshooting

### Connector Not Running
```bash
# Check logs
docker-compose logs kafka-connect

# Check PostgreSQL WAL
docker-compose exec postgres psql -U admin -d clickstream \
  -c "SELECT * FROM pg_replication_slots;"

# Recreate connector
curl -X DELETE http://localhost:8083/connectors/postgres-cdc-connector
curl -X POST -H "Content-Type: application/json" \
  --data @postgres-cdc.json \
  http://localhost:8083/connectors
```

### Spark Streaming Fails
```bash
# Check logs
docker-compose logs spark-master
docker-compose logs spark-worker

# Check MinIO connectivity
mc ls myminio

# Check Kafka connectivity
docker-compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

### Checkpoints Not Created
```bash
# Check config
cat config/spark-conf.yaml

# Check MinIO
mc ls myminio/clickstream-silver/checkpoints/

# Restart Spark
docker-compose restart spark-master spark-worker
```

### Late Data Not Handled
```python
# Check watermark config
print(df_watermarked)

# Test with known late event
insert_event(timestamp=now() - timedelta(minutes=5))

# Check processing time
check_processing_time()
```

---

## Next Steps

After Phase 3 complete:
1. Demo streaming pipeline
2. Compare batch vs streaming latency
3. Proceed to Phase 4 (Backfill Integration)

---

## Estimated Effort

| Task | Hours |
|------|-------|
| 3.1 Debezium Connector | 2 |
| 3.2 Kafka Topics | 1 |
| 3.3 Spark Streaming | 4 |
| 3.4 Schema Registry | 2 |
| 3.5 Checkpoints | 2 |
| 3.6 Late Data | 2 |
| Testing & Debugging | 3 |
| **Total** | **16 hours** |

---

## Notes

- Debezium requires PostgreSQL WAL configuration
- Spark Structured Streaming simpler than Flink (single framework)
- Exactly-once requires checkpointing + idempotent sink
- Watermarks are event-time semantics (not processing time)
- Streaming backfill comes in Phase 4
