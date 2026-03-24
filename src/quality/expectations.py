"""
Data Quality Tests using Great Expectations

Validates clickstream data quality before processing.

Usage:
    python expectations.py --input s3a://clickstream-bronze/clicks/
"""

import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClickstreamExpectations:
    """Data quality expectations for clickstream data"""

    def __init__(self, df):
        self.df = df
        self.results = []
        self.passed = 0
        self.failed = 0

    def expect_column_exists(self, column):
        """Check column exists"""
        try:
            if column in self.df.columns:
                self.passed += 1
                logger.info(f"PASS: Column '{column}' exists")
                return True
            else:
                self.failed += 1
                logger.error(f"FAIL: Column '{column}' missing")
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Column '{column}' - {e}")
            return False

    def expect_column_not_null(self, column):
        """Check column has no nulls"""
        try:
            null_count = self.df.filter(self.df[column].isNull()).count()
            if null_count == 0:
                self.passed += 1
                logger.info(f"PASS: Column '{column}' has no nulls")
                return True
            else:
                self.failed += 1
                pct = null_count / self.df.count() * 100
                logger.error(
                    f"FAIL: Column '{column}' has {null_count} nulls ({pct:.2f}%)"
                )
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Column '{column}' - {e}")
            return False

    def expect_column_unique(self, column):
        """Check column values are unique"""
        try:
            total = self.df.count()
            distinct = self.df.select(column).distinct().count()
            if total == distinct:
                self.passed += 1
                logger.info(f"PASS: Column '{column}' is unique")
                return True
            else:
                duplicates = total - distinct
                pct = duplicates / total * 100
                self.failed += 1
                logger.error(
                    f"FAIL: Column '{column}' has {duplicates} duplicates ({pct:.2f}%)"
                )
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Column '{column}' - {e}")
            return False

    def expect_column_values_in_set(self, column, valid_set):
        """Check column values are in valid set"""
        try:
            invalid = self.df.filter(~self.df[column].isin(valid_set)).count()
            total = self.df.count()
            if invalid == 0:
                self.passed += 1
                logger.info(f"PASS: Column '{column}' values are valid")
                return True
            else:
                pct = invalid / total * 100
                self.failed += 1
                logger.error(
                    f"FAIL: Column '{column}' has {invalid} invalid values ({pct:.2f}%)"
                )
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Column '{column}' - {e}")
            return False

    def expect_row_count_between(self, min_count, max_count):
        """Check row count is within range"""
        try:
            count = self.df.count()
            if min_count <= count <= max_count:
                self.passed += 1
                logger.info(
                    f"PASS: Row count {count} is within range [{min_count}, {max_count}]"
                )
                return True
            else:
                self.failed += 1
                logger.error(
                    f"FAIL: Row count {count} outside range [{min_count}, {max_count}]"
                )
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Row count check - {e}")
            return False

    def expect_column_min(self, column, min_value):
        """Check column minimum value"""
        try:
            min_val = self.df.agg({column: "min"}).collect()[0][0]
            if min_val is not None and min_val >= min_value:
                self.passed += 1
                logger.info(
                    f"PASS: Column '{column}' min value {min_val} >= {min_value}"
                )
                return True
            else:
                self.failed += 1
                logger.error(
                    f"FAIL: Column '{column}' min value {min_val} < {min_value}"
                )
                return False
        except Exception as e:
            self.failed += 1
            logger.error(f"FAIL: Column '{column}' min - {e}")
            return False

    def run_bronze_checks(self):
        """Run bronze layer quality checks"""
        logger.info("Running Bronze Layer Checks...")

        for col_name in [
            "click_id",
            "user_id",
            "session_id",
            "page_url",
            "event_type",
            "event_timestamp",
            "created_at",
            "updated_at",
        ]:
            self.expect_column_exists(col_name)

        self.expect_column_not_null("click_id")
        self.expect_column_unique("click_id")
        self.expect_column_values_in_set(
            "event_type",
            ["page_view", "click", "scroll", "purchase", "form_submit", "video_play"],
        )

        self.expect_row_count_between(1, 10000000)

    def run_silver_checks(self):
        """Run silver layer quality checks"""
        logger.info("Running Silver Layer Checks...")

        self.expect_column_exists("domain")
        self.expect_column_exists("device_type")
        self.expect_column_exists("browser")
        self.expect_column_exists("event_date")

        self.expect_column_not_null("domain")
        self.expect_column_values_in_set("device_type", ["desktop", "mobile", "tablet"])
        self.expect_column_values_in_set(
            "browser", ["Chrome", "Firefox", "Safari", "Edge", "Other"]
        )

    def get_summary(self):
        """Get validation summary"""
        total = self.passed + self.failed
        pct = self.passed / total * 100 if total > 0 else 0

        return {
            "passed": self.passed,
            "failed": self.failed,
            "total": total,
            "pass_rate": pct,
            "success": self.failed == 0,
        }


def validate_bronze(input_path):
    """Validate bronze layer data"""
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("clickstream-dq-bronze")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(input_path)
    logger.info(f"Loaded {df.count()} records from {input_path}")

    validator = ClickstreamExpectations(df)
    validator.run_bronze_checks()

    summary = validator.get_summary()

    print("\n" + "=" * 60)
    print("Bronze Data Quality Results")
    print("=" * 60)
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']:.1f}%")
    print("=" * 60)

    spark.stop()

    return summary["success"]


def validate_silver(input_path):
    """Validate silver layer data"""
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("clickstream-dq-silver")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(input_path)
    logger.info(f"Loaded {df.count()} records from {input_path}")

    validator = ClickstreamExpectations(df)
    validator.run_silver_checks()

    summary = validator.get_summary()

    print("\n" + "=" * 60)
    print("Silver Data Quality Results")
    print("=" * 60)
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']:.1f}%")
    print("=" * 60)

    spark.stop()

    return summary["success"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Quality Validation")
    parser.add_argument("--input", required=True, help="Input Parquet path")
    parser.add_argument(
        "--layer",
        default="bronze",
        choices=["bronze", "silver"],
        help="Data layer to validate",
    )
    args = parser.parse_args()

    if args.layer == "bronze":
        success = validate_bronze(args.input)
    else:
        success = validate_silver(args.input)

    exit(0 if success else 1)
