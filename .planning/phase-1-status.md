# Phase 1: Foundation Setup

## Status: ✅ COMPLETED
## Started: 2024-03-21
## Completed: 2024-03-23

---

## Goals
Get all infrastructure running with sample data and basic batch extraction

### Tasks

#### 1.1 Docker Infrastructure
- [x] Verify docker-compose.yml has all services
- [x] Build and start all containers
- [x] Verify health checks pass
- [x] Document service URLs and credentials

**Services:** PostgreSQL, MinIO, Kafka, Schema Registry, Kafka Connect, Airflow, Spark, Redis

**Commands:**
```bash
docker-compose up -d --build
docker-compose ps
docker-compose logs -f
```

---

#### 1.2 PostgreSQL Setup
- [x] Create init.sql with schema (clicks, sessions tables)
- [x] Add indexes for CDC (updated_at, event_timestamp)
- [x] Generate synthetic data using Faker (100K+ records)
- [x] Verify data count

**Commands:**
```bash
pip install faker tqdm psycopg2-binary
python scripts/generate_sample_data.py
docker-compose exec postgres psql -U admin -d clickstream -c "SELECT COUNT(*) FROM clicks;"
```

---

#### 1.3 MinIO Setup
- [x] Create setup-minio.sh script
- [x] Run script to create buckets: clickstream-bronze, clickstream-silver, clickstream-gold
- [x] Verify access via mc client

**Commands:**
```bash
chmod +x scripts/setup-minio.sh
./scripts/setup-minio.sh
docker-compose exec minio mc ls myminio
```

---

#### 1.4 Basic Airflow DAG
- [x] Create clickstream_batch_dag.py
- [x] Start Airflow services
- [x] Verify DAG visible in UI
- [x] Test manual trigger

**DAG Structure:**
```
extract_clicks_bronze → validate_quality
     ↓                      ↓
  PostgreSQL         MinIO Bronze
```

**Access:** http://localhost:8080 (admin/admin)

---

#### 1.5 Spark Batch Job
- [x] Create bronze_clicks.py
- [x] Copy to docker/spark/jobs/
- [x] Test spark-submit
- [x] Verify Parquet files in MinIO

**Commands:**
```bash
docker-compose exec spark-master spark-submit \
  /opt/spark/jobs/bronze_clicks.py \
  --start-date 2024-01-01 --end-date 2024-01-02

docker-compose exec minio mc ls myminio/clickstream-bronze/clicks/
```

---

## Deliverables

1. ✅ All Docker services defined
2. ✅ PostgreSQL schema created
3. ✅ Data generator script created
4. ✅ MinIO setup script created
5. ✅ Airflow DAG created
6. ✅ Spark bronze job created
7. ✅ **All services running and healthy**

---

## Definition of Done

- [x] `docker-compose ps` shows all services healthy
- [x] PostgreSQL has clicks and sessions tables with data
- [x] MinIO shows 3 buckets
- [x] Airflow DAG can be triggered manually
- [x] Bronze layer Parquet files visible in MinIO

---

## Files Created

```
docker/postgres/init.sql
scripts/generate_sample_data.py
scripts/setup-minio.sh
docker/airflow/dags/clickstream_batch_dag.py
src/batch/bronze_clicks.py
docker/spark/jobs/bronze_clicks.py
src/batch/validate_quality.py
docker/spark/jobs/validate_quality.py
.env
```

---

## Next Action: Proceed to Phase 2

**Next Phase:** [Phase 2: Batch Pipeline](./phase-2-batch-pipeline.md)