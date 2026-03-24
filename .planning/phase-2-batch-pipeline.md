# Phase 2: Complete Batch Pipeline - Detailed Plan

## Status: 🔄 In Progress
## Started: 2024-03-23
## Last Updated: 2026-03-23
## Estimated Duration: 3-4 days
## Priority: High (after Phase 1)

---

## Goals
1. Silver layer with cleaned/enriched data
2. Gold layer with aggregations
3. Great Expectations DQ tests integrated
4. Schema evolution handling
5. Backfill script working
6. Error handling with retries

---

## Task Breakdown

### 2.1 Silver Layer Transformations
**Status:** Pending
**Files:** `src/batch/silver_clicks.py`

**Steps:**
1. Create silver transformation job
2. Clean data (nulls, duplicates)
3. Enrich data (domain, device type)
4. Validate schema
5. Write partitioned by event_date

**Transformations:**
```python
from pyspark.sql.functions import col, regexp_extract, when

# Read bronze
df = spark.read.parquet("s3a://clickstream-bronze/clicks/")

# Clean
df_clean = df \
    .filter(col("click_id").isNotNull()) \
    .filter(col("user_id").isNotNull()) \
    .filter(col("event_type").isin("page_view", "click", "scroll", "purchase"))

# Deduplicate
from pyspark.sql import Window
df_dedup = df_clean \
    .withColumn("rn", row_number().over(
        Window.partitionBy("click_id").orderBy(col("updated_at").desc())
    )) \
    .filter(col("rn") == 1) \
    .drop("rn")

# Enrich: extract domain from URL
df_enriched = df_dedup \
    .withColumn("domain", regexp_extract(col("page_url"), "://([^/]+)", 1))

# Enrich: device type from user agent
df_enriched = df_enriched \
    .withColumn("device_type", when(
        col("user_agent").contains("Mobile"), "mobile"
    ).when(
        col("user_agent").contains("Tablet"), "tablet"
    ).otherwise("desktop"))

# Write silver
df_enriched.write \
    .mode("overwrite") \
    .partitionBy("event_date") \
    .parquet("s3a://clickstream-silver/clicks/")
```

**Acceptance Criteria:**
- [ ] Null values handled
- [ ] Duplicates removed
- [ ] Domain extracted
- [ ] Device type parsed
- [ ] Partitioned by event_date
- [ ] Re-run idempotent

---

### 2.2 Gold Layer Aggregations
**Status:** Pending
**Files:** `src/batch/gold_metrics.py`

**Steps:**
1. Create gold aggregation job
2. Aggregate daily_metrics
3. Aggregate user_sessions
4. Write partitioned outputs

**Aggregations:**
```python
# Read silver
df = spark.read.parquet("s3a://clickstream-silver/clicks/")

# Daily metrics
daily_metrics = df.groupBy(
    col("event_date").alias("date"),
    col("event_type")
).agg(
    count("*").alias("count_events"),
    countDistinct("user_id").alias("unique_users"),
    avg("session_duration").alias("avg_session_duration")
)

daily_metrics.write \
    .mode("overwrite") \
    .partitionBy("date") \
    .parquet("s3a://clickstream-gold/agg/by_date/")

# User sessions
user_sessions = df.groupBy("user_id").agg(
    countDistinct("session_id").alias("session_count"),
    count("*").alias("total_page_views"),
    avg("bounce").alias("bounce_rate")
)

user_sessions.write \
    .mode("overwrite") \
    .partitionBy("user_id") \
    .parquet("s3a://clickstream-gold/by_user/")
```

**Acceptance Criteria:**
- [ ] daily_metrics created
- [ ] user_sessions created
- [ ] Aggregations correct
- [ ] Partitioned appropriately
- [ ] Queryable in Presto/Spark SQL

---

### 2.3 Great Expectations Integration
**Status:** Pending
**Files:** `src/quality/expectations.py`, `docker/airflow/dags/clickstream_batch_dag.py`

**Steps:**
1. Create expectations module
2. Define click expectations
3. Integrate with Airflow DAG
4. Fail on DQ violations
5. Generate DQ reports

**Expectations:**
```python
from great_expectations.dataset import SparkDFDataset

def validate_clicks(df):
    ge_df = SparkDFDataset(df)
    
    # Column existence
    ge_df.expect_column_to_exist("click_id")
    ge_df.expect_column_to_exist("user_id")
    ge_df.expect_column_to_exist("event_type")
    
    # Not null
    ge_df.expect_column_values_to_not_be_null("click_id")
    ge_df.expect_column_values_to_not_be_null("user_id")
    
    # Unique
    ge_df.expect_column_values_to_be_unique("click_id")
    
    # Value ranges
    ge_df.expect_column_values_to_be_between("user_id", min_value=0)
    
    # Allowed values
    ge_df.expect_column_values_to_be_in_set(
        "event_type",
        ["page_view", "click", "scroll", "purchase"]
    )
    
    # Validate
    result = ge_df.validate()
    
    if result["success"]:
        logger.info("All DQ checks passed")
        return True
    else:
        logger.error("DQ checks failed")
        send_alert(result)
        return False
```

**Airflow Integration:**
```python
from airflow.providers.python.operator.python_operator import PythonOperator

def validate_quality(**context):
    from src.quality.expectations import validate_clicks
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder.getOrCreate()
    df = spark.read.parquet("s3a://clickstream-bronze/clicks/")
    
    if not validate_clicks(df):
        raise Exception("Data quality validation failed")
```

**Acceptance Criteria:**
- [ ] Expectations defined
- [ ] Integrated in DAG
- [ ] Pipeline fails on DQ violation
- [ ] DQ report generated
- [ ] Alert sent on failure

---

### 2.4 Schema Evolution Handling
**Status:** Pending
**Files:** `src/utils/schema.py`

**Steps:**
1. Create schema utility
2. Implement mergeSchema option
3. Add validation function
4. Log warnings on new columns
5. Raise on breaking changes

**Code:**
```python
from pyspark.sql.types import DataType, StructType

def read_with_evolution(path):
    """Auto-merge new columns from schema evolution"""
    return spark.read \
        .option("mergeSchema", "true") \
        .parquet(path)

def validate_schema(df, expected_schema):
    """Check if DataFrame schema matches expected"""
    current_schema = {
        field.name: type(field.dataType).__name__
        for field in df.schema
    }
    expected_schema = {
        name: type(dtype).__name__
        for name, dtype in expected_schema.items()
    }
    
    # New columns (OK)
    new_cols = set(current_schema.keys()) - set(expected_schema.keys())
    if new_cols:
        logger.warning(f"New columns detected: {new_cols}")
    
    # Missing columns (BREAKING)
    missing_cols = set(expected_schema.keys()) - set(current_schema.keys())
    if missing_cols:
        raise SchemaValidationError(f"Missing columns: {missing_cols}")
    
    # Type mismatches (BREAKING)
    for col_name in expected_schema.keys():
        if col_name in current_schema:
            if current_schema[col_name] != expected_schema[col_name]:
                raise SchemaValidationError(
                    f"Type mismatch for {col_name}"
                )
```

**Acceptance Criteria:**
- [ ] mergeSchema enabled
- [ ] New columns logged
- [ ] Missing columns raise error
- [ ] Type mismatches raise error
- [ ] Backward compatible

---

### 2.5 Backfill Implementation
**Status:** Pending
**Files:** `scripts/backfill-batch.sh`, `scripts/verify-backfill.py`

**Steps:**
1. Create backfill script
2. Accept start_date, end_date
3. Call Airflow backfill
4. Add verification step
5. Test with date range

**Script:**
```bash
#!/bin/bash
set -euo pipefail

DAG_ID="clickstream_batch_dag"
START_DATE="${1:-}"
END_DATE="${2:-}"

if [ -z "$START_DATE" ] || [ -z "$END_DATE" ]; then
    echo "Usage: $0 <start_date> <end_date>"
    exit 1
fi

echo "Starting batch backfill from $START_DATE to $END_DATE"

# Airflow backfill
airflow dags backfill "$DAG_ID" \
    -s "$START_DATE" \
    -e "$END_DATE" \
    --rerun-failed \
    --local

# Verify
python scripts/verify-backfill.py \
    --start-date "$START_DATE" \
    --end-date "$END_DATE"

echo "Batch backfill complete"
```

**Verification:**
```python
def verify_backfill(start_date, end_date):
    """Verify backfill completed successfully"""
    # Check all dates processed
    dates = get_processed_dates()
    expected_dates = pd.date_range(start_date, end_date)
    
    assert set(dates) == set(expected_dates), \
        "Not all dates processed"
    
    # Check record counts
    counts = get_record_counts()
    assert counts['min'] > 0, "Empty partitions found"
    
    # Check DQ
    dq_results = run_dq_tests()
    assert dq_results['success'], "DQ tests failed"
    
    print("Backfill verification passed")
    return True
```

**Acceptance Criteria:**
- [ ] Script executable
- [ ] Processes date range
- [ ] Verification passes
- [ ] Idempotent (re-run safe)
- [ ] Logs progress

---

### 2.6 Error Handling & Alerting
**Status:** Pending
**Files:** `docker/airflow/dags/clickstream_batch_dag.py`

**Steps:**
1. Add retry logic
2. Configure exponential backoff
3. Add Slack webhook (optional)
4. Log errors to file
5. Create alert template

**Airflow Configuration:**
```python
default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'email': ['data-team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}

dag = DAG(
    'clickstream_batch_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
)
```

**Acceptance Criteria:**
- [ ] Tasks retry on failure
- [ ] Exponential backoff
- [ ] Email alerts configured
- [ ] Error logs informative
- [ ] Retry count logged

---

## Dependencies

```
1.5 Spark Batch Job (Phase 1)
    ↓
2.1 Silver Layer
    ↓
2.2 Gold Layer
    ↓
2.3 Great Expectations
    ↓
2.4 Schema Evolution
    ↓
2.5 Backfill Script
    ↓
2.6 Error Handling
```

---

## Testing Strategy

### Manual Tests
```bash
# Test silver transformation
spark-submit src/batch/silver_clicks.py

# Test gold aggregation
spark-submit src/batch/gold_metrics.py

# Test DQ validation
python -c "from src.quality.expectations import validate_clicks"

# Test backfill
./scripts/backfill-batch.sh 2024-01-01 2024-01-10

# Test idempotency
./scripts/backfill-batch.sh 2024-01-01 2024-01-10
# Run twice, verify same result
```

### Automated Tests
```python
# tests/test_phase2.py
def test_silver_transformation():
    df = run_silver_job()
    assert df.count() > 0
    assert "domain" in df.columns

def test_gold_aggregation():
    df = run_gold_job()
    assert "count_events" in df.columns

def test_dq_validation():
    result = validate_clicks(test_df)
    assert result == True

def test_backfill_idempotency():
    run_backfill("2024-01-01", "2024-01-10")
    count1 = get_record_count()
    run_backfill("2024-01-01", "2024-01-10")
    count2 = get_record_count()
    assert count1 == count2
```

---

## Deliverables Checklist

- [ ] `src/batch/silver_clicks.py` - Silver transformation
- [ ] `src/batch/gold_metrics.py` - Gold aggregation
- [ ] `src/quality/expectations.py` - DQ tests
- [ ] `src/utils/schema.py` - Schema evolution
- [ ] `scripts/backfill-batch.sh` - Backfill script
- [ ] `scripts/verify-backfill.py` - Verification script
- [ ] `tests/test_phase2.py` - Phase 2 tests

---

## Definition of Done

### Functional
- [ ] Bronze → Silver → Gold pipeline runs
- [ ] DQ tests pass or fail appropriately
- [ ] Backfill script processes date range
- [ ] Re-run produces same results
- [ ] Failed tasks retry automatically

### Documentation
- [ ] Phase 2 README updated
- [ ] DQ expectations documented
- [ ] Backfill runbook started
- [ ] Schema evolution guide

### Code Quality
- [ ] Code commented
- [ ] Error handling comprehensive
- [ ] Logs informative
- [ ] No code duplication

---

## Troubleshooting

### Silver Job Fails
```bash
# Check transformation logic
spark-submit --master local src/batch/silver_clicks.py

# Check memory
export SPARK_WORKER_MEMORY=4G

# Check logs
docker-compose logs spark-master
```

### DQ Tests Fail
```python
# Inspect failing data
df.filter(col("click_id").isNull()).show()

# Adjust expectations
# (don't disable, fix data or expectation)
```

### Backfill Stuck
```bash
# Check Airflow logs
docker-compose logs airflow-scheduler

# Check task state
airflow tasks state clickstream_batch_dag extract_clicks 2024-01-01

# Retry task
airflow tasks retry clickstream_batch_dag extract_clicks 2024-01-01
```

### Schema Evolution Error
```python
# Check schema
df.printSchema()

# Check expected schema
print(expected_schema)

# Fix: enable mergeSchema
df.write.option("mergeSchema", "true").parquet(path)
```

---

## Next Steps

After Phase 2 complete:
1. Demo batch pipeline end-to-end
2. Gather feedback on DQ tests
3. Proceed to Phase 3 (Streaming)

---

## Estimated Effort

| Task | Hours |
|------|-------|
| 2.1 Silver Layer | 3 |
| 2.2 Gold Layer | 2 |
| 2.3 Great Expectations | 3 |
| 2.4 Schema Evolution | 2 |
| 2.5 Backfill Script | 2 |
| 2.6 Error Handling | 1 |
| Testing & Debugging | 3 |
| **Total** | **16 hours** |

---

## Notes

- Silver layer is most complex (many transformations)
- DQ tests should be comprehensive but not blocking
- Schema evolution is often overlooked - good differentiator
- Backfill idempotency is critical for production
- Error handling shows production readiness
