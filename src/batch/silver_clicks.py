"""
Spark Batch Job: Transform to Silver Layer

Reads from Bronze layer and performs cleaning and enrichment:
- Remove nulls and duplicates
- Extract domain from URL
- Parse device type from user agent
- Add derived columns

Usage:
    spark-submit silver_clicks.py --start-date 2024-01-01 --end-date 2024-01-10
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_extract, when, row_number, to_date
from pyspark.sql.window import Window
import argparse
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Transform clicks to silver layer")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def create_spark_session():
    spark = (
        SparkSession.builder.appName("clickstream-silver-transform")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def read_bronze(spark, start_date, end_date):
    """Read bronze layer data"""
    bronze_path = "s3a://clickstream-bronze/clicks/"

    print(f"Reading bronze layer: {bronze_path}")
    df = spark.read.parquet(bronze_path)

    print(f"Total bronze records: {df.count()}")
    print(f"Date range: {start_date} to {end_date}")

    return df


def clean_data(df):
    """Remove nulls and invalid records"""
    print("Cleaning data...")

    initial_count = df.count()

    if initial_count == 0:
        print("  No records to clean")
        return df

    df_clean = df.filter(col("click_id").isNotNull())
    df_clean = df_clean.filter(col("user_id").isNotNull())
    df_clean = df_clean.filter(
        col("event_type").isin("page_view", "click", "scroll", "purchase")
    )

    cleaned_count = df_clean.count()
    print(
        f"  Records: {initial_count} -> {cleaned_count} ({cleaned_count / initial_count * 100:.1f}%)"
    )

    return df_clean


def deduplicate(df):
    """Remove duplicate clicks based on click_id"""
    print("Deduplicating...")

    window = Window.partitionBy("click_id").orderBy(col("updated_at").desc())

    df_dedup = (
        df.withColumn("rn", row_number().over(window)).filter(col("rn") == 1).drop("rn")
    )

    before = df.count()
    after = df_dedup.count()
    print(f"  Duplicates removed: {before - after}")

    return df_dedup


def enrich_domain(df):
    """Extract domain from URL"""
    print("Enriching domain...")

    df = df.withColumn("domain", regexp_extract(col("page_url"), "://([^/]+)", 1))

    return df


def enrich_device_type(df):
    """Parse device type from user agent"""
    print("Enriching device type...")

    df = df.withColumn(
        "device_type",
        when(col("user_agent").contains("Mobile"), "mobile")
        .when(col("user_agent").contains("Tablet"), "tablet")
        .when(col("user_agent").contains("iPhone"), "mobile")
        .when(col("user_agent").contains("Android"), "mobile")
        .otherwise("desktop"),
    )

    df = df.withColumn(
        "browser",
        when(col("user_agent").contains("Chrome"), "Chrome")
        .when(col("user_agent").contains("Firefox"), "Firefox")
        .when(col("user_agent").contains("Safari"), "Safari")
        .when(col("user_agent").contains("Edge"), "Edge")
        .otherwise("Other"),
    )

    return df


def add_event_date(df):
    """Add event_date partition column"""
    df = df.withColumn("event_date", to_date(col("event_timestamp")))
    return df


def write_silver(df):
    """Write to Silver layer"""
    silver_path = "s3a://clickstream-silver/clicks/"

    print(f"Writing to Silver layer: {silver_path}")

    df.write.mode("overwrite").partitionBy("event_date").parquet(silver_path)

    print("Silver write complete")


def main():
    args = parse_args()

    print("=" * 60)
    print("Clickstream Silver Transformation")
    print("=" * 60)
    print(f"Start date: {args.start_date}")
    print(f"End date:   {args.end_date}")
    print("=" * 60)

    spark = create_spark_session()

    try:
        df = read_bronze(spark, args.start_date, args.end_date)
        print(f"\nBronze records: {df.count()}")

        df = clean_data(df)
        df = deduplicate(df)
        df = enrich_domain(df)
        df = enrich_device_type(df)
        df = add_event_date(df)

        print("\nSample enriched data:")
        df.select("click_id", "domain", "device_type", "browser", "event_date").show(
            5, truncate=False
        )

        write_silver(df)

        print("\n" + "=" * 60)
        print("Silver Transformation Complete")
        print("=" * 60)
        print(f"Records written: {df.count()}")
        print(f"Output: s3a://clickstream-silver/clicks/")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
