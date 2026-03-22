# Docker Environment Setup

## Services

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** | 5432 | Source database with clickstream data |
| **MinIO** | 9000 (API), 9001 (Console) | S3-compatible data lake storage |
| **Kafka** | 29092 | Event streaming platform |
| **Schema Registry** | 8081 | Avro schema management |
| **Kafka Connect** | 8083 | CDC connector (Debezium) |
| **Airflow** | 8080 | Orchestration UI |
| **Spark Master** | 8081 (UI), 7077 (RPC) | Batch processing |
| **Flink JobManager** | 8082 (UI) | Stream processing |
| **Redis** | 6379 | Caching/metadata store |

## Quick Start

### 1. First-time setup
```bash
# Build and start all services
docker-compose up -d --build

# Initialize Airflow metadata DB and admin user
# This runs automatically because airflow-webserver and airflow-scheduler depend on airflow-init.

# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

### 2. Access UIs
- **Airflow**: http://localhost:8080 (admin/admin)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)
- **Spark Master**: http://localhost:8081
- **Flink Dashboard**: http://localhost:8082
- **Schema Registry**: http://localhost:8081

Airflow admin credentials are provisioned by the `airflow-init` service using values from `.env`.

### 3. Initialize MinIO buckets
```bash
# Create buckets via MinIO client
docker-compose exec minio mc alias set myminio http://minio:9000 minioadmin minioadmin123
docker-compose exec minio mc mb myminio/clickstream-bronze
docker-compose exec minio mc mb myminio/clickstream-silver
docker-compose exec minio mc mb myminio/clickstream-gold
```

### 4. Verify PostgreSQL
```bash
docker-compose exec postgres psql -U admin -d clickstream -c "SELECT COUNT(*) FROM clicks;"
```

## Configuration Files

- `docker-compose.yml` - All service definitions
- `config/application.yml` - Shared application config
- `config/flink-conf.yaml` - Flink-specific settings
- `.env` - Environment variables

## Service Directories

```
docker/
├── airflow/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── dags/           # Mount DAGs here
│   ├── logs/           # Airflow logs
│   ├── plugins/        # Custom plugins
│   └── scripts/        # Helper scripts
├── spark/
│   ├── Dockerfile
│   └── jobs/           # Spark job scripts
├── flink/
│   ├── Dockerfile
│   └── jobs/           # Flink job JARs
└── postgres/
    └── init.sql        # Database initialization
```

## Troubleshooting

### Check service logs
```bash
docker-compose logs <service-name>
```

### Restart a service
```bash
docker-compose restart <service-name>
```

### Rebuild all services
```bash
docker-compose up -d --build --force-recreate
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d --build
```

### Kafka Connect plugins
Debezium PostgreSQL connector is auto-installed during Kafka Connect startup.
Check installation:
```bash
curl http://localhost:8083/connector-plugins | jq
```

## Resource Allocation

Default memory settings (adjust in `.env` for production):
- Spark Executor: 2G
- Spark Driver: 1G
- Flink TaskManager: 1024m
- 2 task slots per TaskManager
