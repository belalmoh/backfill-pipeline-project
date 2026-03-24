# Project Planning Index

---

## Planning Documents

### Core Plans
| Document | Purpose | Status |
|----------|---------|--------|
| [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | Complete project roadmap with all phases | ✅ Complete |
| [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) | Key technology choices and trade-offs | ✅ Complete |
| [INTERVIEW_PREP.md](./INTERVIEW_PREP.md) | Interview preparation guide | ✅ Complete |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | Commands and configs cheat sheet | ✅ Complete |

### Phase Plans
| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| [Phase 1: Foundation](./phase-1-foundation.md) | Docker, PostgreSQL, MinIO, basic batch | 2-3 days | ✅ Complete |
| [Phase 2: Batch Pipeline](./phase-2-batch-pipeline.md) | Silver/Gold, DQ, backfill | 3-4 days | 🔄 In Progress |
| [Phase 3: Streaming](./phase-3-streaming.md) | Debezium, Kafka, Spark Streaming | 3-4 days | ⏳ Pending |
| [Phase 4: Backfill](./phase-4-backfill.md) | Batch + streaming backfill, idempotency | 2-3 days | ⏳ Pending |
| [Phase 5: Production](./phase-5-production.md) | Monitoring, alerting, chaos tests | 2-3 days | ⏳ Pending |

---

## Project Status

### Current Phase: Phase 2 - Batch Pipeline
**Last Updated:** 2026-03-23
**Status:** 🔄 In Progress

### Progress Tracker
```
Phase 1: Foundation        [██████████] 100%
Phase 2: Batch Pipeline    [███░░░░░░░░] 40%  (Bronze done, Silver/Gold ready)
Phase 3: Streaming         [          ] 0%
Phase 4: Backfill          [          ] 0%
Phase 5: Production        [          ] 0%
-----------------------------------------
Overall                  [██░░░░░░░░░░] 25%
```

---

## Technology Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Source DB | PostgreSQL 15 | ✅ Running |
| Data Lake | MinIO (S3-compatible) | ✅ Running |
| Orchestration | Apache Airflow 2.7.0 | ✅ Running |
| Batch Processing | Apache Spark 3.4.0 | ✅ Running |
| Streaming | Spark Structured Streaming 3.4.0 | ✅ Ready |
| Message Queue | Apache Kafka 7.6.0 | ✅ Running |
| CDC | Debezium PostgreSQL 1.9.8 | ✅ Running |
| Schema Registry | Confluent Schema Registry | ✅ Running |
| Data Quality | Great Expectations | ✅ Installed |
| Sample Data | Faker library | ✅ Generated |

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│              Clickstream Analytics Pipeline             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PostgreSQL ──┬──→ Batch (Spark) ──→ Bronze/Silver/Gold│
│  (clicks)     │                                        │
│               │                                        │
│               └──→ CDC (Debezium) ──→ Kafka ──→ Spark   │
│                                    Streaming ──→ Silver│
│                                                         │
│  Backfill: Batch for history + Stream for current      │
│  DQ: Great Expectations validation                     │
│  Idempotency: Partition overwrite                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| Spark Master | http://localhost:8082 | - |
| Schema Registry | http://localhost:8085 | - |
| Kafka Connect | http://localhost:8083 | - |
| PostgreSQL | localhost:5432 | admin / admin123 |
| Kafka (host) | localhost:29092 | - |
| Redis | localhost:6379 | - |

---

## Getting Started

### Quick Start
```bash
# Start all services
make start

# Check status
make status

# Stop all services
make stop
```

### Manual Commands
```bash
# Build and start all services
docker-compose up -d --build

# Verify services
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Next Steps

### Begin Phase 2: Batch Pipeline
1. Create Spark silver layer job (clean/transform)
2. Create Spark gold layer job (aggregations)
3. Add Great Expectations data quality checks
4. Create Airflow DAG for full batch pipeline

**Current Phase:** [Phase 2: Batch Pipeline](./phase-2-batch-pipeline.md)

---

## File Structure

```
.planning/
├── INDEX.md                      # This file
├── IMPLEMENTATION_PLAN.md        # Complete roadmap
├── ARCHITECTURE_DECISIONS.md     # Tech choices
├── INTERVIEW_PREP.md             # Interview guide
├── QUICK_REFERENCE.md            # Commands cheat sheet
├── phase-1-foundation.md         # Phase 1 tasks ✅ Complete
├── phase-2-batch-pipeline.md     # Phase 2 tasks 🔄 In Progress
├── phase-3-streaming.md          # Phase 3 tasks ⏳ Pending
├── phase-4-backfill.md           # Phase 4 tasks ⏳ Pending
└── phase-5-production.md         # Phase 5 tasks ⏳ Pending

Project Root:
├── docker-compose.yml            # All services
├── Makefile                      # Management commands
├── PROJECT_PLAN.md               # High-level overview
├── docker/                       # Service configs
├── src/                          # Processing code
├── scripts/                      # Shell scripts
└── tests/                        # Test files
```