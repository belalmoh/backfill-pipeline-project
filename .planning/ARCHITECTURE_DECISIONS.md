# Architecture Decision Record (ADR)

## Date: 2024-03-21
## Status: Approved

---

## Context
Building a production-grade clickstream analytics pipeline for interview preparation. Need to make key architecture decisions that reflect real-world production systems.

---

## Decision

### 1. Infrastructure: Docker-First
**Decision:** All services run in Docker containers via docker-compose

**Rationale:**
- Reproducible environment
- Easy to tear down and rebuild
- Matches production containerization patterns
- No local dependency conflicts
- Can be deployed to K8s later

**Trade-offs:**
- Higher resource usage (RAM/CPU)
- Slightly slower startup
- Network debugging complexity

---

### 2. Processing: Spark for Batch + Streaming
**Decision:** Use Spark Structured Streaming for both batch and streaming

**Rationale:**
- Single framework for both paradigms
- Python ecosystem (PySpark)
- Mature, production-tested
- Demonstrates understanding of batch + streaming
- Simpler operations (one framework vs two)
- Interview-friendly (Spark widely used)

**Trade-offs:**
- Spark Streaming higher latency than Flink (minutes vs seconds)
- Flink more advanced for complex event processing
- But Spark sufficient for most use cases

---

### 3. CDC: Debezium
**Decision:** Use Debezium PostgreSQL connector for change data capture

**Rationale:**
- Battle-tested, production-grade
- Handles schema evolution
- Exactly-once semantics
- No custom code needed
- Industry standard

**Trade-offs:**
- PostgreSQL WAL configuration required
- Additional service to monitor
- Learning curve for debugging

---

### 4. Data Lake: MinIO with Parquet
**Decision:** Use MinIO (S3-compatible) with Parquet format

**Rationale:**
- S3-compatible = portable to AWS/GCS
- Parquet = columnar, compressed, schema evolution
- MinIO = self-hosted, no cost
- Industry standard pattern

**Trade-offs:**
- MinIO vs real S3 (but easier for dev)
- Parquet not human-readable (but efficient)

---

### 5. Data Quality: Great Expectations
**Decision:** Use Great Expectations for data validation

**Rationale:**
- De-facto standard for DQ
- Rich expectation library
- Integrates with Airflow
- Generates documentation
- Portable expectations

**Trade-offs:**
- Additional dependency
- Learning curve
- Runtime overhead

---

### 6. Orchestration: Airflow
**Decision:** Use Apache Airflow for batch orchestration

**Rationale:**
- Industry standard
- Python-based (team familiarity)
- Rich ecosystem of providers
- Backfill built-in
- UI for monitoring

**Trade-offs:**
- Operational overhead
- Not ideal for streaming
- DAG complexity for simple jobs

---

### 7. Language: Python (PySpark)
**Decision:** Use Python for all processing code

**Rationale:**
- Single language across stack
- Faster development
- Rich data ecosystem (Faker, pandas)
- Interview-friendly (common language)
- PySpark production-ready

**Trade-offs:**
- Performance vs Scala
- GIL limitations

---

### 8. Backfill: Hybrid Approach
**Decision:** Batch for history + Streaming for current

**Rationale:**
- Batch: Idempotent, controllable, auditable
- Streaming: Real-time, low latency
- Hybrid: Best of both
- Matches real-world patterns

**Trade-offs:**
- Complexity in handoff
- Need to prevent duplicates
- More code to maintain

---

### 9. Schema: Evolution-First
**Decision:** Design for schema evolution from start

**Rationale:**
- Real-world requirement
- Demonstrates senior thinking
- Backward compatible by default
- Uses Parquet mergeSchema

**Trade-offs:**
- More complex code
- Need versioning strategy
- Testing complexity

---

### 10. Testing: Multi-Layer
**Decision:** Unit + Integration + Chaos tests

**Rationale:**
- Unit: Fast, isolated
- Integration: End-to-end
- Chaos: Production readiness
- Demonstrates testing maturity

**Trade-offs:**
- More test code
- Longer test suite
- Chaos testing complexity

---

## Consequences

### Positive
- Production-grade architecture
- Demonstrates Spark batch + streaming
- Interview-ready talking points
- Portable to cloud (S3, K8s)
- Modern best practices
- Simpler stack (no Flink to learn)

### Negative
- High complexity
- Steep learning curve
- Resource-intensive
- Longer implementation time

### Neutral
- Requires Docker knowledge
- Needs monitoring setup
- Multiple services to debug

---

## Compliance

### Patterns Followed
- Medallion Architecture (Bronze/Silver/Gold)
- Lambda Architecture (batch + streaming)
- Event-Driven Architecture (Kafka)
- Data Mesh principles (domain-oriented)

### Anti-Patterns Avoided
- No monolithic batch jobs
- No hard-coded credentials
- No schema-on-read only
- No untested idempotency

---

## Alternatives Considered

| Decision | Alternative | Why Rejected |
|----------|-------------|--------------|
| Docker | Local install | Not reproducible, conflicts |
| Spark only | Spark + Flink | Unnecessary complexity, learning curve |
| Debezium | Custom CDC | Reinventing wheel, error-prone |
| MinIO | AWS S3 | Cost, slower iteration |
| Great Expectations | Custom validation | Less feature-rich, more code |
| Airflow | Prefect | Less mature, smaller ecosystem |
| Python | Scala | Slower dev, interview-unfriendly |
| Hybrid backfill | Batch only | Not real-time, outdated pattern |

---

## Notes for Interview

### Architecture Talking Points
1. **Why Spark for both?** Single framework, simpler operations, sufficient for most use cases
2. **Why CDC?** Avoid polling, real-time, efficient
3. **Why Parquet?** Columnar, predicate pushdown, schema evolution
4. **Why exactly-once?** Business requirements, no duplicates
5. **Why backfill?** Historical analysis, reprocessing

### Trade-off Discussions
- "We chose Spark over Flink because simplicity > micro-optimization for this use case"
- "For production, we'd move to AWS S3 and K8s"
- "This demonstrates the pattern; scale is implementation detail"

### Failure Scenarios
- Kafka down → Spark Streaming waits, replays on recovery
- MinIO down → Spark checkpoints, no data loss
- Schema change → Backward compatible, new columns null
- Duplicate event → Idempotent write handles it

---

## References
- [Medallion Architecture - Databricks](https://databricks.com/glossary/medallion-architecture)
- [Lambda Architecture - Nathan Marz](https://nathanmarz.com/blog/how-to-beat-the-cap-theorem.html)
- [Debezium Documentation](https://debezium.io/documentation/)
- [Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
