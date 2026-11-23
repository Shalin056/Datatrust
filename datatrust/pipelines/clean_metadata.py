"""
clean_metadata.py — the Spark cleaning job: raw JSONL files -> one clean Parquet table.

  data/raw/datasets.jsonl ─┐
                           ├─► join ─► clean fields ─► not-a-dataset flag ─┐
  data/raw/cards.jsonl ────┘                                               │
                                                  data/clean/datasets.parquet ◄┘

One row per dataset, with real timestamps, tag lists, license results, card section results,
and the likely_not_a_dataset flag.
The per-dataset logic lives in clean_rules.py (plain Python); this file only does the Spark work.

Run (from the project folder, Docker Desktop open):
  docker compose run --rm pipeline python -m datatrust.pipelines.clean_metadata

Imports / uses: datatrust/pipelines/spark_session.py, raw_schemas.py, clean_rules.py,
                datatrust/config.py, pyspark
Used by: you (command line); later datatrust/pipelines/run_pipeline.py and Step 5 checks
"""

import sys

from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from datatrust.config import load_settings, project_path
from datatrust.pipelines.clean_rules import (
    BULK_UPLOAD_MIN_REPOS,
    build_clean_fields,
    load_all_rules,
    not_a_dataset_reasons,
)
from datatrust.pipelines.raw_schemas import CARDS_SCHEMA, DATASETS_SCHEMA
from datatrust.pipelines.spark_session import create_spark

# The shape of what build_clean_fields() returns. Spark needs to know it in advance.
CLEAN_FIELDS_SCHEMA = StructType([
    StructField("languages", ArrayType(StringType())),
    StructField("task_categories", ArrayType(StringType())),
    StructField("modalities", ArrayType(StringType())),
    StructField("size_category", StringType()),
    StructField("arxiv_ids", ArrayType(StringType())),
    StructField("source_datasets", ArrayType(StringType())),
    StructField("license_ids", ArrayType(StringType())),
    StructField("license_source", StringType()),
    StructField("license_category", StringType()),
    StructField("license_detail", StringType()),
    StructField("has_multiple_licenses", BooleanType()),
    StructField("has_card", BooleanType()),
    StructField("has_front_matter", BooleanType()),
    StructField("card_word_count", LongType()),
    StructField("sections_found", ArrayType(StringType())),
    StructField("empty_sections", ArrayType(StringType())),
    StructField("description_text", StringType()),
    StructField("sources_text", StringType()),
])


# Reads the two raw files with our hand-written schemas.
# Inputs: spark — the SparkSession; raw_dir — folder with the JSONL files.
# Returns: (datasets DataFrame, cards DataFrame).
def read_raw(spark, raw_dir):
    datasets = spark.read.json(str(raw_dir / "datasets.jsonl"), schema=DATASETS_SCHEMA)
    cards = spark.read.json(str(raw_dir / "cards.jsonl"), schema=CARDS_SCHEMA)
    return datasets, cards


# Joins each dataset with its card. A LEFT join keeps every dataset, even one with
# no card row at all (its card columns are then empty/null).
# Inputs: datasets, cards — DataFrames from read_raw().
# Returns: one DataFrame, one row per dataset.
def join_cards(datasets, cards):
    card_columns = cards.select(
        "dataset_id",
        F.col("status").alias("card_status"),
        "card_text",
    )
    return datasets.join(card_columns, on="dataset_id", how="left")


# Adds the clean fields by running build_clean_fields() on every row.
# A "UDF" (user-defined function) lets Spark call our own Python function for each row.
# Inputs: joined — DataFrame from join_cards(); rules — from load_all_rules().
# Returns: DataFrame with a "clean" struct column holding all derived fields.
def add_clean_fields(joined, rules):
    # The rules are loaded once here and shipped to Spark's workers together with the function.
    def build(tags, tag_licenses, card_data, card_text, card_status):
        return build_clean_fields(tags, tag_licenses, card_data, card_text, card_status, rules)

    build_udf = F.udf(build, CLEAN_FIELDS_SCHEMA)
    return joined.withColumn(
        "clean",
        build_udf("tags", "license_from_tags", "card_data", "card_text", "card_status"),
    )


# Picks and tidies the final columns: real timestamps, simple flags, and the clean fields.
# Inputs: enriched — DataFrame from add_clean_fields().
# Returns: the final clean DataFrame.
def select_final_columns(enriched):
    # Text like "2024-12-19T11:34:03.000Z" becomes a real timestamp Spark can do maths with.
    created_at = F.to_timestamp("created_at")
    last_modified = F.to_timestamp("last_modified")
    collected_at = F.to_timestamp("collected_at")

    return enriched.select(
        "dataset_id",
        "author",
        # "owner/name" -> "name" (element_at with -1 = the last piece).
        F.element_at(F.split("dataset_id", "/"), -1).alias("dataset_name"),
        F.coalesce("downloads", F.lit(0)).alias("downloads"),
        F.coalesce("likes", F.lit(0)).alias("likes"),
        created_at.alias("created_at"),
        last_modified.alias("last_modified"),
        collected_at.alias("collected_at"),
        # How old the last update was on the day we collected the data.
        F.datediff(collected_at, last_modified).alias("days_since_update"),
        # gated is "false", "auto" or "manual"; anything but "false" = you must ask for access.
        (F.coalesce("gated", F.lit("false")) != "false").alias("is_gated"),
        F.col("gated").alias("gated_mode"),
        F.coalesce("card_status", F.lit("not_fetched")).alias("card_status"),
        "description",
        "tags",
        "clean.*",
    )


# Finds "bulk uploaders": owners with many repos in our collection and a README on none.
# This needs ALL rows of an owner at once, which is why it is a Spark groupBy and not
# part of the per-row Python rules.
# Inputs: clean — DataFrame from select_final_columns().
# Returns: DataFrame with one row per bulk-uploading author: (author, is_bulk_uploader=True).
def find_bulk_uploaders(clean):
    per_author = clean.groupBy("author").agg(
        F.count("*").alias("repo_count"),
        # has_card is True/False; cast to 1/0 and add up = number of documented repos.
        F.sum(F.col("has_card").cast("int")).alias("documented_count"),
    )
    return per_author.filter(
        (F.col("repo_count") >= BULK_UPLOAD_MIN_REPOS) & (F.col("documented_count") == 0)
    ).select("author", F.lit(True).alias("is_bulk_uploader"))


# Adds likely_not_a_dataset (True/False) and not_a_dataset_reasons (list) to every row.
# Inputs: clean — DataFrame from select_final_columns().
# Returns: the same DataFrame with the two new columns.
def add_not_a_dataset_flag(clean):
    # Left join: authors who are not bulk uploaders get null, which we turn into False.
    with_bulk = clean.join(find_bulk_uploaders(clean), on="author", how="left").withColumn(
        "is_bulk_uploader", F.coalesce("is_bulk_uploader", F.lit(False))
    )
    reasons_udf = F.udf(not_a_dataset_reasons, ArrayType(StringType()))
    with_reasons = with_bulk.withColumn(
        "not_a_dataset_reasons", reasons_udf("has_card", "tags", "is_bulk_uploader")
    )
    return with_reasons.withColumn(
        "likely_not_a_dataset", F.size("not_a_dataset_reasons") > 0
    ).drop("is_bulk_uploader")


# Stops the job if the clean table is not what we expect (data quality checks).
# Inputs: clean — the final DataFrame; expected_rows — number of raw datasets.
# Returns: nothing. Raises ValueError with a clear message if a check fails.
def check_quality(clean, expected_rows):
    row_count = clean.count()
    if row_count != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows but got {row_count}")

    duplicate_ids = clean.groupBy("dataset_id").count().filter("count > 1").count()
    if duplicate_ids:
        raise ValueError(f"{duplicate_ids} dataset_id values appear more than once")

    missing_ids = clean.filter(F.col("dataset_id").isNull()).count()
    if missing_ids:
        raise ValueError(f"{missing_ids} rows have no dataset_id")


# Prints a short summary so you can see the job did something sensible.
# Inputs: clean — the final DataFrame (already written).
# Returns: nothing.
def print_summary(clean):
    print("\n===== Clean table columns =====")
    clean.printSchema()
    print("===== Where licenses came from =====")
    clean.groupBy("license_source").count().orderBy(F.desc("count")).show()
    print("===== License categories =====")
    clean.groupBy("license_category").count().orderBy(F.desc("count")).show()
    print("===== Likely not a dataset =====")
    clean.groupBy("likely_not_a_dataset", "not_a_dataset_reasons").count().orderBy(
        F.desc("count")
    ).show(truncate=False)
    print("===== Days since last update (on collection day) =====")
    clean.select(
        F.min("days_since_update").alias("min"),
        F.expr("percentile_approx(days_since_update, 0.5)").alias("median"),
        F.max("days_since_update").alias("max"),
    ).show()


# Runs the whole cleaning job.
# Inputs: none (paths come from configs/settings.yaml).
# Returns: 0 if it worked, 1 if the raw files are missing.
def main():
    settings = load_settings()
    raw_dir = project_path(settings["paths"]["raw_dir"])
    clean_dir = project_path(settings["paths"]["clean_dir"])
    output_path = clean_dir / "datasets.parquet"

    for name in ("datasets.jsonl", "cards.jsonl"):
        if not (raw_dir / name).exists():
            print(f"Missing {raw_dir / name}. Run the collector first (Step 3).")
            return 1

    spark = create_spark("clean_metadata")
    datasets, cards = read_raw(spark, raw_dir)
    expected_rows = datasets.count()

    clean = select_final_columns(add_clean_fields(join_cards(datasets, cards), load_all_rules()))
    clean = add_not_a_dataset_flag(clean)
    # cache() keeps the result in memory, so the checks, the write, and the summary
    # don't each re-run the whole (slow) Python cleaning step.
    clean = clean.cache()
    check_quality(clean, expected_rows)

    # Our table is small, so one file (coalesce(1)) is easier to handle than many part files.
    clean.coalesce(1).write.mode("overwrite").parquet(str(output_path))
    print(f"\nWrote {expected_rows} rows to {output_path}")

    print_summary(spark.read.parquet(str(output_path)))
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
