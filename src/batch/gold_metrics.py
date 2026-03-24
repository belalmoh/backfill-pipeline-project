"""
Spark Batch Job: Create Gold Layer Aggregations

Reads from Silver layer and creates aggregated metrics:
- Daily metrics (clicks, users, sessions by type)
- User session summaries
- Domain popularity

Usage:
    spark-submit gold_metrics.py --date 2024-01-01
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    count,
    countDistinct,
    avg,
    sum as spark_sum,
    hour,
    dayofweek,
)
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Create gold layer aggregations")
    parser.add_argument("--date", required=False, help="Date to aggregate (YYYY-MM-DD)")
    return parser.parse_args()


def create_spark_session():
    spark = (
        SparkSession.builder.appName("clickstream-gold-agg")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def create_daily_metrics(df, date):
    """Create daily event metrics"""
    print("Creating daily metrics...")

    daily = (
        df.groupBy("event_date", "event_type")
        .agg(
            count("*").alias("event_count"),
            countDistinct("user_id").alias("unique_users"),
            countDistinct("session_id").alias("unique_sessions"),
            countDistinct("domain").alias("unique_domains"),
        )
        .withColumnRenamed("event_date", "date")
    )

    output_path = f"s3a://clickstream-gold/daily_metrics/date={date}/"
    daily.write.mode("overwrite").parquet(output_path)

    print(f"  Daily metrics: {daily.count()} rows")
    return daily


def create_hourly_metrics(df, date):
    """Create hourly event metrics"""
    print("Creating hourly metrics...")

    from pyspark.sql.functions import hour as hr

    hourly = (
        df.withColumn("hour", hr(col("event_timestamp")))
        .groupBy("event_date", "hour", "event_type")
        .agg(
            count("*").alias("event_count"),
            countDistinct("user_id").alias("unique_users"),
        )
        .withColumnRenamed("event_date", "date")
    )

    output_path = f"s3a://clickstream-gold/hourly_metrics/date={date}/"
    hourly.write.mode("overwrite").parquet(output_path)

    print(f"  Hourly metrics: {hourly.count()} rows")
    return hourly


def create_domain_metrics(df, date):
    """Create domain popularity metrics"""
    print("Creating domain metrics...")

    domain = (
        df.groupBy("event_date", "domain", "device_type")
        .agg(
            count("*").alias("page_views"),
            countDistinct("user_id").alias("unique_users"),
            countDistinct("session_id").alias("sessions"),
        )
        .withColumnRenamed("event_date", "date")
        .orderBy(col("page_views").desc())
    )

    output_path = f"s3a://clickstream-gold/domain_metrics/date={date}/"
    domain.write.mode("overwrite").parquet(output_path)

    print(f"  Domain metrics: {domain.count()} rows")
    return domain


def create_user_summary(df, date):
    """Create user session summaries"""
    print("Creating user summaries...")

    user_summary = (
        df.groupBy("event_date", "user_id")
        .agg(
            count("*").alias("total_events"),
            countDistinct("session_id").alias("sessions"),
            countDistinct("event_type").alias("event_types"),
            countDistinct("domain").alias("domains_visited"),
            avg(
                col("event_timestamp").cast("long") - col("created_at").cast("long")
            ).alias("avg_session_duration_sec"),
        )
        .withColumnRenamed("event_date", "date")
    )

    output_path = f"s3a://clickstream-gold/user_summary/date={date}/"
    user_summary.write.mode("overwrite").parquet(output_path)

    print(f"  User summaries: {user_summary.count()} rows")
    return user_summary


def create_device_metrics(df, date):
    """Create device breakdown metrics"""
    print("Creating device metrics...")

    device = (
        df.groupBy("event_date", "device_type", "browser")
        .agg(
            count("*").alias("event_count"),
            countDistinct("user_id").alias("unique_users"),
        )
        .withColumnRenamed("event_date", "date")
    )

    output_path = f"s3a://clickstream-gold/device_metrics/date={date}/"
    device.write.mode("overwrite").parquet(output_path)

    print(f"  Device metrics: {device.count()} rows")
    return device


def main():
    args = parse_args()

    print("=" * 60)
    print("Clickstream Gold Aggregation")
    print("=" * 60)
    print(f"Date: {args.date}")
    print("=" * 60)

    spark = create_spark_session()

    try:
        silver_path = "s3a://clickstream-silver/clicks/"
        df = spark.read.parquet(silver_path)

        # Filter by date if specified, otherwise process all
        if args.date:
            df = df.filter(col("event_date") == args.date)
            target_date = args.date
        else:
            # Get all unique dates
            dates = [
                row.event_date for row in df.select("event_date").distinct().collect()
            ]
            print(f"\nFound {len(dates)} dates to process")
            target_date = None

        record_count = df.count()
        print(f"\nSilver records: {record_count}")

        if record_count == 0:
            print("No data found")
            return

        if target_date:
            create_daily_metrics(df, target_date)
            create_hourly_metrics(df, target_date)
            create_domain_metrics(df, target_date)
            create_user_summary(df, target_date)
            create_device_metrics(df, target_date)
        else:
            # Process each date separately
            for date in dates:
                date_str = str(date)
                print(f"\nProcessing date: {date_str}")
                date_df = df.filter(col("event_date") == date)
                create_daily_metrics(date_df, date_str)
                create_hourly_metrics(date_df, date_str)
                create_domain_metrics(date_df, date_str)
                create_user_summary(date_df, date_str)
                create_device_metrics(date_df, date_str)

        print("\n" + "=" * 60)
        print("Gold Aggregation Complete")
        print("=" * 60)
        print(f"Records processed: {record_count}")
        print("Outputs:")
        print("  - s3a://clickstream-gold/daily_metrics/")
        print("  - s3a://clickstream-gold/hourly_metrics/")
        print("  - s3a://clickstream-gold/domain_metrics/")
        print("  - s3a://clickstream-gold/user_summary/")
        print("  - s3a://clickstream-gold/device_metrics/")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
