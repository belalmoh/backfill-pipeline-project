"""
Airflow DAG: Clickstream Batch Pipeline

Uses SparkSubmitOperator for production-ready Spark job execution
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


S3A_PACKAGES = (
    "org.apache.hadoop:hadoop-aws:3.3.4,"
    "com.amazonaws:aws-java-sdk-bundle:1.12.262"
)
BRONZE_PACKAGES = (
    "org.postgresql:postgresql:42.6.0,"
    "org.apache.hadoop:hadoop-aws:3.3.4,"
    "com.amazonaws:aws-java-sdk-bundle:1.12.262"
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="clickstream_batch_pipeline",
    default_args=default_args,
    description="Clickstream batch pipeline: Bronze -> Silver -> Gold",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["clickstream", "batch", "pipeline"],
) as dag:
    # Bronze extraction from PostgreSQL
    bronze_extract = SparkSubmitOperator(
        task_id="bronze_extract",
        application="/opt/spark/jobs/bronze_clicks.py",
        application_args=[
            "--start-date",
            "{{ ds }}",
            "--end-date",
            "{{ ds }}",
        ],
        conn_id="spark-default",
        packages=BRONZE_PACKAGES,
    )

    # Silver transformation
    silver_transform = SparkSubmitOperator(
        task_id="silver_transform",
        application="/opt/spark/jobs/silver_clicks.py",
        application_args=[
            "--start-date",
            "{{ ds }}",
            "--end-date",
            "{{ ds }}",
        ],
        conn_id="spark-default",
        packages=S3A_PACKAGES,
    )

    # Gold aggregation
    gold_aggregate = SparkSubmitOperator(
        task_id="gold_aggregate",
        application="/opt/spark/jobs/gold_metrics.py",
        application_args=[
            "--date",
            "{{ ds }}",
        ],
        conn_id="spark-default",
        packages=S3A_PACKAGES,
    )

    bronze_extract >> silver_transform >> gold_aggregate
