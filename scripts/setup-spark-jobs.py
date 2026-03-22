"""
Spark Job: Copy to jobs directory for Airflow execution

This script copies the bronze_clicks.py to the Spark jobs directory
so Airflow can execute it via SparkSubmitOperator.
"""

import shutil
import os

# Source and destination
src = (
    "/Users/belal/Desktop/Projects/backfill-pipeline-project/src/batch/bronze_clicks.py"
)
dst = "/Users/belal/Desktop/Projects/backfill-pipeline-project/docker/spark/jobs/bronze_clicks.py"

# Copy file
shutil.copy(src, dst)
print(f"✅ Copied bronze_clicks.py to docker/spark/jobs/")

# Also copy for src directory
os.makedirs("docker/spark/jobs", exist_ok=True)
shutil.copy(src, "docker/spark/jobs/bronze_clicks.py")
print(f"✅ Bronze job ready for Spark submit")
