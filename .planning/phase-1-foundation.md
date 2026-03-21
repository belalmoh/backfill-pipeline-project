# Phase 1: Foundation - Detailed Plan

## Status: Not Started
## Estimated Duration: 2-3 days
## Priority: High

---

## Goals
1. All Docker services running and healthy
2. PostgreSQL populated with synthetic clickstream data
3. MinIO buckets created
4. Basic Airflow DAG visible in UI
5. Spark job writes to bronze layer

---

## Task Breakdown

### 1.1 Verify Docker Infrastructure
**Status:** Pending
**Files:** `docker-compose.yml`, `.env`

**Steps:**
1. Review docker-compose.yml for all services
2. Review .env for correct credentials
3. Build and start all containers
4. Verify health checks pass
5. Document service URLs

**Commands:**
```bash
# Build and start
docker-compose up -d --build

# Check status (all should be "Up")
docker-compose ps

# Verify health
docker-compose logs postgres | grep "ready to accept connections"
docker-compose logs minio | grep "API"
docker-compose logs kafka | grep "started"
```

**Acceptance Criteria:**
- [ ] All 12 services show "Up" status
- [ ] No error logs
- [ ] Health endpoints return 200

**Blockers:**
- Port conflicts (check if ports already in use)
- Resource limits (increase Docker memory if needed)

---

### 1.2 PostgreSQL Setup
**Status:** Pending
**Files:** `docker/postgres/init.sql`, `scripts/generate_sample_data.py`

**Steps:**
1. Create init.sql with schema
2. Add indexes for CDC
3. Generate synthetic data (Faker library)
4. Verify data count

**Schema:**
```sql
CREATE TABLE clicks (
    click_id          BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    session_id        VARCHAR(100) NOT NULL,
    page_url          TEXT NOT NULL,
    event_type        VARCHAR(50),
    event_timestamp   TIMESTAMP NOT NULL,
    user_agent        TEXT,
    ip_address        INET,
    referrer_url      TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clicks_updated_at ON clicks(updated_at);
CREATE INDEX idx_clicks_event_timestamp ON clicks(event_timestamp);

CREATE TABLE sessions (
    session_id        VARCHAR(100) PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    started_at        TIMESTAMP NOT NULL,
    ended_at          TIMESTAMP,
    duration_seconds  INT,
    page_views_count  INT DEFAULT 0,
    bounce            BOOLEAN DEFAULT false,
    traffic_source    VARCHAR(50),
    device_type       VARCHAR(50),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Data Generation Script:**
```python
# scripts/generate_sample_data.py
from faker import Faker
from datetime import datetime, timedelta
import random
import psycopg2

fake = Faker()

# Generate 100K clicks
# Date range: 2024-01-01 to 2024-03-21
# Event types: page_view, click, scroll, purchase
# Traffic sources: organic, paid, direct, referral
# Device types: desktop, mobile, tablet
```

**Acceptance Criteria:**
- [ ] Tables created (clicks, sessions)
- [ ] Indexes created
- [ ] 100K+ click records
- [ ] 10K+ session records
- [ ] Data spans 2.5 months

**Blockers:**
- Faker performance (batch inserts, not one-by-one)
- Memory limits (generate in chunks)

---

### 1.3 MinIO Setup
**Status:** Pending
**Files:** `scripts/setup-minio.sh`

**Steps:**
1. Create setup script
2. Create 3 buckets (bronze, silver, gold)
3. Verify bucket creation
4. Test upload/download

**Commands:**
```bash
# Create buckets
docker-compose exec minio mc alias set myminio \
  http://minio:9000 minioadmin minioadmin123

docker-compose exec minio mc mb myminio/clickstream-bronze
docker-compose exec minio mc mb myminio/clickstream-silver
docker-compose exec minio mc mb myminio/clickstream-gold

# Verify
mc ls myminio
```

**Acceptance Criteria:**
- [ ] 3 buckets created
- [ ] mc client configured
- [ ] Can upload file
- [ ] Can download file

**Blockers:**
- MinIO not started (check health)
- mc client not found (install in MinIO container)

---

### 1.4 Basic Airflow DAG
**Status:** Pending
**Files:** `docker/airflow/dags/clickstream_batch_dag.py`

**Steps:**
1. Create DAG file
2. Define extract task (PostgreSQL → Spark)
3. Define write task (Spark → MinIO)
4. Set daily schedule
5. Test manual trigger

**DAG Structure:**
```python
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit \
    import SparkSubmitOperator
from datetime import datetime, timedelta

default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'clickstream_batch_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
)

extract = SparkSubmitOperator(
    task_id='extract_clicks',
    application='/opt/spark/jobs/bronze_clicks.py',
    conn_id='spark-default',
    dag=dag,
)
```

**Acceptance Criteria:**
- [ ] DAG visible in Airflow UI
- [ ] Can trigger manually
- [ ] Task runs successfully
- [ ] Logs visible

**Blockers:**
- Airflow not initialized (wait for webserver)
- DAG parse errors (check Python syntax)
- Spark connection (verify spark-master URL)

---

### 1.5 Spark Batch Job
**Status:** Pending
**Files:** `src/batch/bronze_clicks.py`, `docker/spark/jobs/bronze_clicks.py`

**Steps:**
1. Create Spark job
2. Read from PostgreSQL via JDBC
3. Write to MinIO as Parquet
4. Partition by extract_date
5. Test idempotent write

**Code:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_date

spark = SparkSession.builder \
    .appName("bronze_clicks") \
    .getOrCreate()

# Read from PostgreSQL
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres:5432/clickstream") \
    .option("user", "admin") \
    .option("password", "admin123") \
    .option("dbtable", "clicks") \
    .load()

# Add extract date
df = df.withColumn("extract_date", current_date())

# Write to MinIO
df.write \
    .mode("overwrite") \
    .partitionBy("extract_date") \
    .parquet("s3a://clickstream-bronze/clicks/")
```

**Acceptance Criteria:**
- [ ] Job runs via Airflow
- [ ] Parquet files created in MinIO
- [ ] Partitioned by date
- [ ] Re-run produces same result

**Blockers:**
- JDBC driver missing (add to Spark classpath)
- S3A connector missing (add to Spark Dockerfile)
- MinIO credentials (set AWS env vars)

---

## Dependencies

```
1.1 Docker Infrastructure
    ↓
1.2 PostgreSQL Setup
    ↓
1.3 MinIO Setup
    ↓
1.4 Airflow DAG
    ↓
1.5 Spark Batch Job
```

---

## Testing Strategy

### Manual Tests
```bash
# 1. Verify all services running
docker-compose ps

# 2. Verify PostgreSQL data
docker-compose exec postgres psql -U admin -d clickstream \
  -c "SELECT COUNT(*) FROM clicks;"

# 3. Verify MinIO buckets
mc ls myminio

# 4. Trigger Airflow DAG
airflow dags trigger clickstream_batch_dag

# 5. Verify MinIO data
mc ls myminio/clickstream-bronze/clicks/
```

### Automated Tests
```python
# tests/test_phase1.py
def test_postgres_data_count():
    count = get_click_count()
    assert count >= 100000

def test_minio_buckets_exist():
    buckets = list_buckets()
    assert 'clickstream-bronze' in buckets

def test_airflow_dag_exists():
    dags = list_dags()
    assert 'clickstream_batch_dag' in dags

def test_spark_job_runs():
    result = run_spark_job('bronze_clicks.py')
    assert result.exit_code == 0
```

---

## Deliverables Checklist

- [ ] `docker/postgres/init.sql` - Database schema
- [ ] `scripts/generate_sample_data.py` - Data generator
- [ ] `scripts/setup-minio.sh` - MinIO setup script
- [ ] `docker/airflow/dags/clickstream_batch_dag.py` - Basic DAG
- [ ] `src/batch/bronze_clicks.py` - Spark bronze job
- [ ] `tests/test_phase1.py` - Phase 1 tests

---

## Definition of Done

### Functional
- [ ] All services healthy (`docker-compose ps` shows Up)
- [ ] PostgreSQL has 100K+ clicks
- [ ] MinIO has 3 buckets
- [ ] Airflow DAG visible and triggerable
- [ ] Spark job writes Parquet to bronze

### Documentation
- [ ] README updated with Phase 1 status
- [ ] Service URLs documented
- [ ] Troubleshooting guide started

### Code Quality
- [ ] Code commented
- [ ] No hardcoded credentials
- [ ] Error handling added
- [ ] Logs informative

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs <service>

# Check port conflicts
lsof -i :5432
lsof -i :9000

# Restart
docker-compose restart <service>
```

### Data Generation Slow
```python
# Use batch inserts
cursor.executemany(insert_sql, batch_data)
# Not: cursor.execute(insert_sql, data)  # one-by-one
```

### Airflow DAG Not Visible
```bash
# Check syntax
python -m py_compile docker/airflow/dags/clickstream_batch_dag.py

# Check Airflow logs
docker-compose logs airflow-scheduler

# Touch file to trigger refresh
touch docker/airflow/dags/clickstream_batch_dag.py
```

### Spark Job Fails
```bash
# Check Spark logs
docker-compose logs spark-master

# Increase memory
export SPARK_WORKER_MEMORY=4G

# Test locally
spark-submit --master local src/batch/bronze_clicks.py
```

---

## Next Steps

After Phase 1 complete:
1. Review architecture with stakeholder
2. Gather feedback on data model
3. Proceed to Phase 2 (Batch Pipeline Complete)

---

## Estimated Effort

| Task | Hours |
|------|-------|
| 1.1 Docker Infrastructure | 1 |
| 1.2 PostgreSQL Setup | 2 |
| 1.3 MinIO Setup | 0.5 |
| 1.4 Airflow DAG | 2 |
| 1.5 Spark Batch Job | 3 |
| Testing & Debugging | 2 |
| **Total** | **10.5 hours** |

---

## Notes

- Start with minimal viable setup
- Don't optimize prematurely
- Focus on end-to-end flow first
- Add complexity in later phases
- Document as you go
