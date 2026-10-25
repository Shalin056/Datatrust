"""
inspect_raw.py — a first, read-only look at the raw data using Spark.
It changes nothing; it prints counts so we understand the data BEFORE writing cleaning rules.

Run (from the project folder, Docker Desktop open):
  docker compose run --rm pipeline python -m datatrust.pipelines.inspect_raw

Imports / uses: datatrust/pipelines/spark_session.py, datatrust/pipelines/raw_schemas.py,
                datatrust/config.py, pyspark,
                data/raw/datasets.jsonl, data/raw/cards.jsonl
Used by: you (command line)
"""

import sys

from pyspark.sql import functions as F

from datatrust.config import load_settings, project_path
from datatrust.pipelines.raw_schemas import CARDS_SCHEMA, DATASETS_SCHEMA
from datatrust.pipelines.spark_session import create_spark


# Prints a title line so the output is easy to scan.
# Inputs: title — text to show.
# Returns: nothing.
def print_title(title):
    print(f"\n===== {title} =====")


# Reads the raw files with Spark and prints a few simple summaries.
# Inputs: none (paths come from configs/settings.yaml).
# Returns: 0 if it worked, 1 if the raw files are missing.
def main():
    settings = load_settings()
    raw_dir = project_path(settings["paths"]["raw_dir"])
    datasets_path = raw_dir / "datasets.jsonl"
    cards_path = raw_dir / "cards.jsonl"

    # Fail early with a clear message instead of a long Spark error.
    for path in (datasets_path, cards_path):
        if not path.exists():
            print(f"Missing {path}. Run the collector first (Step 3).")
            return 1

    spark = create_spark("inspect_raw")

    # spark.read.json reads JSONL (one JSON object per line) into a DataFrame
    # (a table with named columns, spread across CPU cores).
    # We pass our own schema instead of letting Spark guess (see raw_schemas.py for why).
    datasets = spark.read.json(str(datasets_path), schema=DATASETS_SCHEMA)
    cards = spark.read.json(str(cards_path), schema=CARDS_SCHEMA)

    print_title("Row counts")
    print(f"datasets: {datasets.count()}")
    print(f"cards:    {cards.count()}")

    print_title("Columns in datasets.jsonl")
    datasets.printSchema()

    print_title("Sample: license_from_card values that are lists")
    # A list arrives as text starting with "[" because our schema says StringType.
    datasets.filter(F.col("license_from_card").startswith("[")).select(
        "dataset_id", "license_from_card"
    ).show(5, truncate=False)

    print_title("Card status counts")
    cards.groupBy("status").count().orderBy(F.desc("count")).show()

    print_title("Top 15 licenses (from tags)")
    # license_from_tags is a LIST per dataset. explode() turns one row with a list
    # into one row per list item, so each license gets counted.
    licenses = datasets.select(F.explode_outer("license_from_tags").alias("license"))
    licenses.groupBy("license").count().orderBy(F.desc("count")).show(15, truncate=False)

    print_title("Datasets with no license tag at all")
    no_license = datasets.filter(F.size("license_from_tags") == 0).count()
    print(f"{no_license} of {datasets.count()}")

    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
