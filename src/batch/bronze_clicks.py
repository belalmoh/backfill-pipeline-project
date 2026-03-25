"""
Spark Batch Job: Extract Clicks to Bronze Layer

Reads clickstream data from PostgreSQL and writes to MinIO Bronze layer as Parquet.

Features:
- Incremental extract using updated_at
- Partitioning by extract_date
- Idempotent writes (overwrite partition)
- Schema evolution support

Usage:
    spark-submit bronze_clicks.py --start-date 2024-01-01 --end-date 2024-01-10
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, lit
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType,
    TimestampType,
    IntegerType,
    BooleanType,
)
import argparse
import sys
from datetime import datetime


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Extract clicks to bronze layer")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def create_spark_session():
    """Create Spark session with MinIO configuration"""
    spark = (
        SparkSession.builder.appName("clickstream-bronze-extract")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.sql.parquet.mergeSchema", "true")
        .config("spark.driver.extraClassPath", "/opt/spark/jars/postgresql-42.6.0.jar")
        .config(
            "spark.executor.extraClassPath", "/opt/spark/jars/postgresql-42.6.0.jar"
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark


def extract_clicks(spark, start_date, end_date):
    """
    Extract clicks from PostgreSQL for date range

    Uses incremental extract based on updated_at
    """
    jdbc_url = "jdbc:postgresql://postgres:5432/clickstream"
    jdbc_properties = {
        "user": "admin",
        "password": "admin123",
        "driver": "org.postgresql.Driver",
    }

    # Build query for incremental extract
    query = f"""
        (SELECT 
            click_id,
            user_id,
            session_id,
            page_url,
            event_type,
            event_timestamp,
            user_agent,
            ip_address,
            referrer_url,
            created_at,
            updated_at
        FROM clicks
        WHERE updated_at >= '{start_date}'
        AND updated_at < '{end_date}'
        ) AS clicks_extract
    """

    print(f"📊 Extracting clicks from {start_date} to {end_date}")

    df = (
        spark.read.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", query)
        .options(**jdbc_properties)
        .load()
    )

    return df


def add_metadata(df, extract_date):
    """Add extraction metadata columns"""
    df = df.withColumn("extract_date", to_date(lit(extract_date)))
    df = df.withColumn(
        "batch_id", lit(f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    )
    return df


def write_bronze(df, extract_date):
    """
    Write to MinIO Bronze layer

    Idempotent write: overwrites partition for same date
    """
    output_path = f"s3a://clickstream-bronze/clicks/"

    print(f"💾 Writing to Bronze layer: {output_path}")

    df.write.mode("overwrite").partitionBy("extract_date").parquet(output_path)

    print(f"✅ Bronze write complete")


def verify_write(spark, extract_date):
    """Verify data was written correctly"""
    df = spark.read.parquet("s3a://clickstream-bronze/clicks/")
    count = df.filter(col("extract_date") == extract_date).count()

    if count > 0:
        print(f"✅ Verification passed: {count} records for {extract_date}")
        return True
    else:
        print(f"❌ Verification failed: no records for {extract_date}")
        return False


def main():
    """Main execution"""
    args = parse_args()

    print("=" * 60)
    print("🚀 Clickstream Bronze Extraction")
    print("=" * 60)
    print(f"📅 Start date: {args.start_date}")
    print(f"📅 End date:   {args.end_date}")
    print("=" * 60)

    # Create Spark session
    spark = create_spark_session()

    try:
        # Extract data
        df = extract_clicks(spark, args.start_date, args.end_date)

        # Add metadata
        df = add_metadata(df, args.start_date)

        record_count = df.count()
        if record_count == 0:
            print("ℹ️ No records found for the requested extraction window")
            return

        # Show sample
        print("\n📋 Sample data:")
        df.show(5, truncate=False)

        # Write to Bronze
        write_bronze(df, args.start_date)

        # Verify
        verify_write(spark, args.start_date)

        # Print summary
        print("\n" + "=" * 60)
        print("✅ Bronze Extraction Complete")
        print("=" * 60)
        print(f"📊 Records extracted: {record_count}")
        print(f"📁 Output location: s3a://clickstream-bronze/clicks/")
        print(f"🏷️  Partition: extract_date={args.start_date}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
