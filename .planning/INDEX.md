# Project Planning Index

## Overview
This directory contains detailed implementation plans for the Clickstream Analytics Pipeline project.

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
| [Phase 1: Foundation](./phase-1-foundation.md) | Docker, PostgreSQL, MinIO, basic batch | 2-3 days | ⏳ Pending |
| [Phase 2: Batch Pipeline](./phase-2-batch-pipeline.md) | Silver/Gold, DQ, backfill | 3-4 days | ⏳ Pending |
| [Phase 3: Streaming](./phase-3-streaming.md) | Debezium, Flink, Kafka | 3-4 days | ⏳ Pending |
| [Phase 4: Backfill](./phase-4-backfill.md) | Batch + streaming backfill, idempotency | 2-3 days | ⏳ Pending |
| [Phase 5: Production](./phase-5-production.md) | Monitoring, alerting, chaos tests | 2-3 days | ⏳ Pending |

---

## Project Status

### Current Phase: Not Started
**Next Action:** Begin Phase 1 - Foundation

### Progress Tracker
```
Phase 1: Foundation        [          ] 0%
Phase 2: Batch Pipeline    [          ] 0%
Phase 3: Streaming         [          ] 0%
Phase 4: Backfill          [          ] 0%
Phase 5: Production        [          ] 0%
-----------------------------------------
Overall                  [          ] 0%
```

---

## Technology Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Source DB | PostgreSQL 15 | ✅ Ready |
| Data Lake | MinIO (S3-compatible) | ✅ Ready |
| Orchestration | Apache Airflow 2.8.1 | ✅ Ready |
| Batch Processing | Apache Spark 3.5.1 (Python) | ✅ Ready |
| Streaming | Spark Structured Streaming 3.5.1 | ✅ Ready |
| Message Queue | Apache Kafka 7.6.0 | ✅ Ready |
| CDC | Debezium PostgreSQL | ✅ Ready |
| Schema Registry | Confluent Schema Registry | ✅ Ready |
| Data Quality | Great Expectations 0.18.21 | ✅ Ready |
| Sample Data | Faker library | ✅ Ready |

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
│               └──→ CDC (Debezium) ──→ Kafka ──→ Spark │
│                                    Streaming ──→ Silver│
│                                                         │
│  Backfill: Batch for history + Stream for current      │
│  DQ: Great Expectations validation                     │
│  Idempotency: Partition overwrite                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. Medallion Architecture
- **Bronze:** Raw, untransformed data
- **Silver:** Cleaned, enriched, validated
- **Gold:** Aggregated, business-ready

### 2. Lambda Architecture
- **Batch:** Accurate, comprehensive, historical
- **Streaming:** Fast, real-time, current
- **Combined:** Best of both worlds

### 3. Backfill Strategies
- **Batch:** Airflow backfill command, idempotent
- **Streaming:** Kafka offset replay
- **Hybrid:** Batch history + stream current

### 4. Exactly-Once Semantics
- Kafka: Idempotent producer
- Flink: Checkpointing
- Sink: Idempotent writes

### 5. Schema Evolution
- Backward compatible (add columns)
- Breaking changes (remove/type change)
- Parquet mergeSchema option

---

## Success Criteria

| Criterion | Definition | Target |
|-----------|------------|--------|
| Functional | Pipelines process data correctly | ✅ |
| Idempotent | Re-runs produce identical results | ✅ |
| Backfillable | Can backfill any date range | ✅ |
| Schema Evolution | Handles new columns | ✅ |
| Data Quality | DQ tests pass | ✅ |
| Observability | Metrics, logs, alerts | ✅ |
| Documentation | Runbook complete | ✅ |

---

## Interview Preparation

### System Design Topics
- Lambda architecture trade-offs
- CDC vs polling
- Batch vs streaming
- Schema evolution strategies
- Exactly-once semantics

### Coding Topics
- Spark transformations
- Idempotent writes
- Watermark configuration
- Data quality tests

### Behavioral Topics
- Production incident handling
- Trade-off discussions
- Collaboration examples

---

## Getting Started

### 1. Review Plans
```bash
# Read implementation plan
cat .planning/IMPLEMENTATION_PLAN.md

# Read architecture decisions
cat .planning/ARCHITECTURE_DECISIONS.md

# Read phase 1 plan
cat .planning/phase-1-foundation.md
```

### 2. Start Infrastructure
```bash
# Build and start all services
docker-compose up -d --build

# Verify services
docker-compose ps

# Check logs
docker-compose logs -f
```

### 3. Begin Phase 1
Follow tasks in `phase-1-foundation.md`:
1. Verify Docker infrastructure
2. Set up PostgreSQL schema
3. Generate sample data
4. Create MinIO buckets
5. Build basic Airflow DAG
6. Implement Spark bronze job

---

## Quick Commands

```bash
# Start project
docker-compose up -d --build

# Check status
docker-compose ps

# View Airflow UI
open http://localhost:8080

# View MinIO console
open http://localhost:9001

# Generate sample data
python scripts/generate_sample_data.py

# Run backfill
./scripts/backfill-batch.sh 2024-01-01 2024-03-21

# Run tests
pytest tests/

# Stop project
docker-compose down
```

---

## File Structure

```
.planning/
├── INDEX.md                      # This file
├── IMPLEMENTATION_PLAN.md        # Complete roadmap
├── ARCHITECTURE_DECISIONS.md     # Tech choices
├── INTERVIEW_PREP.md             # Interview guide
├── QUICK_REFERENCE.md            # Commands cheat sheet
├── phase-1-foundation.md         # Phase 1 tasks
├── phase-2-batch-pipeline.md     # Phase 2 tasks
├── phase-3-streaming.md          # Phase 3 tasks
├── phase-4-backfill.md           # Phase 4 tasks
└── phase-5-production.md         # Phase 5 tasks

Project Root:
├── docker-compose.yml            # All services
├── PROJECT_PLAN.md               # High-level overview
├── docker/                       # Service configs
├── src/                          # Processing code
├── scripts/                      # Shell scripts
├── tests/                        # Test files
└── docs/                         # Documentation
```

---

## Resuming After Pause

### If You Pause and Return

1. **Check Current Phase:**
   ```bash
   # Review progress
   cat .planning/INDEX.md
   
   # Check last completed phase
   ls -la src/batch/    # Phase 2
   ls -la src/streaming/ # Phase 3
   ```

2. **Verify Infrastructure:**
   ```bash
   # Check services running
   docker-compose ps
   
   # Restart if needed
   docker-compose up -d
   ```

3. **Resume Tasks:**
   - Open the phase plan for current phase
   - Check completed tasks
   - Continue with next pending task

4. **Run Tests:**
   ```bash
   # Verify existing functionality
   pytest tests/test_phase*.py -v
   ```

---

## Contact & Resources

### Documentation
- [Airflow Docs](https://airflow.apache.org/docs/)
- [Spark Docs](https://spark.apache.org/docs/)
- [Flink Docs](https://flink.apache.org/docs/)
- [Debezium Docs](https://debezium.io/documentation/)
- [Great Expectations](https://greatexpectations.io/docs/)

### Blogs
- Netflix Tech Blog
- Uber Engineering Blog
- Databricks Blog

### Books
- "Designing Data-Intensive Applications" - Kleppmann
- "Fundamentals of Data Engineering" - Reis & Housley

---

## Next Steps

1. **Review** all planning documents
2. **Start** Phase 1: Foundation
3. **Complete** each phase sequentially
4. **Test** thoroughly at each phase
5. **Document** as you build
6. **Prepare** for interview

**Ready to begin? Start with Phase 1!**

```bash
# Phase 1 first task: Verify Docker infrastructure
docker-compose up -d --build
docker-compose ps
```
