# Quick Reference - Commands & Configs

## Docker Management

```bash
# Start all services (build if needed)
docker-compose up -d --build

# Start specific service
docker-compose up -d postgres minio

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Check service status
docker-compose ps

# View logs (follow)
docker-compose logs -f <service>

# View logs (last 100 lines)
docker-compose logs --tail=100 <service>

# Restart service
docker-compose restart <service>

# Rebuild specific service
docker-compose up -d --build <service>

# Execute command in container
docker-compose exec <service> <command>

# Remove orphan containers
docker-compose down --remove-orphans
```

---

## PostgreSQL

```bash
# Connect to database
docker-compose exec postgres psql -U admin -d clickstream

# Run SQL query
docker-compose exec postgres psql -U admin -d clickstream \
  -c "SELECT COUNT(*) FROM clicks;"

# Show tables
docker-compose exec postgres psql -U admin -d clickstream \
  -c "\dt"

# Describe table
docker-compose exec postgres psql -U admin -d clickstream \
  -c "\d clicks"

# Export data
docker-compose exec postgres pg_dump -U admin clickstream > backup.sql

# Import data
docker-compose exec -T postgres psql -U admin -d clickstream < backup.sql

# Reset database
docker-compose exec postgres psql -U admin -d clickstream \
  -c "TRUNCATE clicks, sessions RESTART IDENTITY CASCADE;"
```

---

## MinIO

```bash
# Configure alias
docker-compose exec minio mc alias set myminio \
  http://minio:9000 minioadmin minioadmin123

# List buckets
mc ls myminio

# Create bucket
mc mb myminio/clickstream-bronze

# Upload file
mc cp file.parquet myminio/clickstream-bronze/clicks/

# Download file
mc cp myminio/clickstream-bronze/clicks/file.parquet ./

# Remove bucket (recursive, force)
mc rm --recursive --force myminio/clickstream-bronze/

# Show bucket info
mc stat myminio/clickstream-bronze/

# Watch bucket
mc watch myminio/clickstream-bronze/
```

---

## Kafka

```bash
# List topics
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 --list

# Describe topic
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 \
  --describe --topic dbserver1.public.clicks

# Create topic
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 \
  --create --topic clicks --partitions 3 --replication-factor 1

# Delete topic
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:9092 \
  --delete --topic clicks

# Produce messages
docker-compose exec kafka kafka-console-producer \
  --bootstrap-server kafka:9092 --topic clicks

# Consume messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic clicks --from-beginning

# Consumer groups
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 --list

# Describe consumer group
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --group flink-consumer --describe

# Reset offset (to earliest)
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --group flink-consumer --topic clicks \
  --reset-to-earliest --execute

# Reset offset (to latest)
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --group flink-consumer --topic clicks \
  --reset-to-latest --execute

# Reset offset (to specific offset)
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --group flink-consumer --topic clicks \
  --reset-to-offset 100 --execute
```

---

## Schema Registry

```bash
# List subjects
curl http://localhost:8081/subjects

# Get schema
curl http://localhost:8081/subjects/clicks-value/versions/latest

# Delete schema
curl -X DELETE http://localhost:8081/subjects/clicks-value

# Check compatibility
curl -X POST -H "Content-Type: application/json" \
  --data @new_schema.json \
  http://localhost:8081/config/subjects/clicks-value/compatibility
```

---

## Kafka Connect

```bash
# List connectors
curl http://localhost:8083/connector-plugins | jq

# List running connectors
curl http://localhost:8083/connectors | jq

# Get connector info
curl http://localhost:8083/connectors/postgres-cdc-connector | jq

# Get connector status
curl http://localhost:8083/connectors/postgres-cdc-connector/status | jq

# Create connector
curl -X POST -H "Content-Type: application/json" \
  --data @postgres-cdc.json \
  http://localhost:8083/connectors | jq

# Delete connector
curl -X DELETE http://localhost:8083/connectors/postgres-cdc-connector

# Restart connector
curl -X POST http://localhost:8083/connectors/postgres-cdc-connector/restart

# Pause connector
curl -X PUT http://localhost:8083/connectors/postgres-cdc-connector/pause

# Resume connector
curl -X PUT http://localhost:8083/connectors/postgres-cdc-connector/resume
```

---

## Airflow

```bash
# List DAGs
docker-compose exec airflow-webserver airflow dags list

# Trigger DAG
docker-compose exec airflow-webserver airflow dags trigger clickstream_batch_dag

# Backfill
docker-compose exec airflow-webserver airflow dags backfill \
  clickstream_batch_dag -s 2024-01-01 -e 2024-03-21

# DAG state
docker-compose exec airflow-webserver airflow dags state \
  clickstream_batch_dag 2024-03-21

# Task state
docker-compose exec airflow-webserver airflow tasks state \
  clickstream_batch_dag extract_clicks 2024-03-21

# Retry task
docker-compose exec airflow-webserver airflow tasks retry \
  clickstream_batch_dag extract_clicks 2024-03-21

# List tasks
docker-compose exec airflow-webserver airflow tasks list \
  clickstream_batch_dag --tree
```

---

## Spark

```bash
# Submit job
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode cluster \
  --conf spark.driver.memory=1g \
  --conf spark.executor.memory=2g \
  /opt/spark/jobs/bronze_clicks.py

# Submit with arguments
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark/jobs/bronze_clicks.py \
  --start-date 2024-01-01 --end-date 2024-01-10

# Check Spark UI
open http://localhost:8081

# View job logs
docker-compose logs spark-master
docker-compose logs spark-worker
```

---

## Spark Structured Streaming

```bash
# Submit streaming job
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark/jobs/streaming_clicks.py

# Submit with arguments
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.driver.memory=1g \
  /opt/spark/jobs/streaming_clicks.py

# Check Spark UI
open http://localhost:8081

# View job logs
docker-compose logs spark-master
docker-compose logs spark-worker
```

---

## Backfill Scripts

```bash
# Batch backfill
./scripts/backfill-batch.sh 2024-01-01 2024-03-21

# Streaming backfill (offset replay)
./scripts/backfill-streaming.sh earliest

# Hybrid backfill
./scripts/backfill-hybrid.sh 2024-01-01 2024-03-21

# Verify backfill
python scripts/verify-backfill.py \
  --start-date 2024-01-01 \
  --end-date 2024-03-21
```

---

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_batch_pipeline.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run integration tests
pytest tests/test_integration.py -v -m integration

# Run chaos tests
pytest tests/test_chaos.py -v -m chaos
```

---

## Environment Variables

```bash
# View .env file
cat .env

# Export variables
export $(cat .env | xargs)

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

## Debugging

```bash
# Check container logs
docker-compose logs <service>

# Follow logs
docker-compose logs -f <service>

# Last 100 lines
docker-compose logs --tail=100 <service>

# Check container status
docker-compose ps

# Inspect container
docker inspect <container_id>

# Execute shell in container
docker-compose exec <service> /bin/bash

# Check disk usage
docker system df

# Check volume usage
docker volume ls
```

---

## Reset Commands

```bash
# Reset everything (nuclear option)
docker-compose down -v
docker-compose up -d --build

# Reset PostgreSQL only
docker-compose down postgres
docker volume rm postgres_data
docker-compose up -d postgres

# Reset MinIO only
docker-compose down minio
docker volume rm minio_data
docker-compose up -d minio

# Reset Kafka offsets
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9092 \
  --all-groups --reset-to-earliest --dry-run

# Reset Airflow DB
docker-compose exec airflow-webserver airflow db reset -y
```

---

## Useful Aliases

```bash
# Add to ~/.zshrc or ~/.bashrc

alias dc='docker-compose'
alias dcp='docker-compose ps'
alias dcl='docker-compose logs -f'
alias dcup='docker-compose up -d --build'
alias dcdo='docker-compose down'

alias psql='docker-compose exec postgres psql -U admin -d clickstream'
alias minio='docker-compose exec minio mc'
alias kafka='docker-compose exec kafka'
alias airflow='docker-compose exec airflow-webserver airflow'
alias spark='docker-compose exec spark-master'
alias flink='docker-compose exec flink-jobmanager flink'
```

---

## File Locations

```
# Project structure
backfill-pipeline-project/
├── docker-compose.yml          # Main compose file
├── .env                        # Environment variables
├── PROJECT_PLAN.md            # High-level plan
├── IMPLEMENTATION_PLAN.md     # Detailed tasks
├── docker/
│   ├── airflow/
│   │   ├── dags/              # Airflow DAGs
│   │   └── scripts/           # Helper scripts
│   ├── spark/
│   │   └── jobs/              # Spark job scripts
│   ├── flink/
│   │   └── jobs/              # Flink job JARs
│   ├── kafka/
│   │   └── connect/           # Connector configs
│   └── postgres/
│       └── init.sql           # DB init script
├── src/
│   ├── batch/                 # Batch processing code
│   ├── streaming/             # Streaming code
│   └── utils/                 # Shared utilities
├── scripts/                   # Shell scripts
├── tests/                     # Test files
└── docs/                      # Documentation
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

### Spark Streaming Job Stuck
```bash
# Check job status
docker-compose logs spark-master

# Stop streaming (Ctrl+C in terminal)

# Clear checkpoint if needed
mc rm --recursive --force myminio/clickstream-silver/checkpoints/

# Restart
docker-compose exec spark-master spark-submit /opt/spark/jobs/streaming_clicks.py
```
