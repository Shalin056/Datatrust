"""
raw_schemas.py — the exact column names and types of our raw JSONL files, written out by hand.
A "schema" is the list of columns in a table and the type of each one (text, number, list...).

Why not let Spark guess? On our real data, guessing CRASHED: two dataset cards use the
same field with different capital letters ("formats" vs "Formats"), and Spark treats
those as the same column. Writing the schema ourselves also makes reading faster
(no guessing pass) and means a strange new dataset can never change our table shape.

Imports / uses: pyspark
Used by: datatrust/pipelines/inspect_raw.py (and later the cleaning jobs)
"""

from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# Columns of data/raw/datasets.jsonl (written by datatrust/collector/fetch_datasets.py).
DATASETS_SCHEMA = StructType([
    StructField("dataset_id", StringType()),
    StructField("author", StringType()),
    StructField("license_from_tags", ArrayType(StringType())),
    # Usually text like "mit", but some cards give a list. Reading it as StringType keeps
    # either form as plain text (a list arrives as '["mit","apache-2.0"]'); we parse it
    # properly in the cleaning step.
    StructField("license_from_card", StringType()),
    StructField("tags", ArrayType(StringType())),
    StructField("downloads", LongType()),
    StructField("likes", LongType()),
    # Dates stay as text for now; the cleaning step turns them into real timestamps.
    StructField("created_at", StringType()),
    StructField("last_modified", StringType()),
    # "gated" can be false, "auto" or "manual", so text is the only safe type.
    StructField("gated", StringType()),
    StructField("private", BooleanType()),
    StructField("disabled", BooleanType()),
    StructField("description", StringType()),
    # The whole card header kept as one JSON text, which avoids the "Formats" crash.
    StructField("card_data", StringType()),
    StructField("collected_at", StringType()),
])

# Columns of data/raw/cards.jsonl (written by datatrust/collector/fetch_cards.py).
CARDS_SCHEMA = StructType([
    StructField("dataset_id", StringType()),
    StructField("status", StringType()),
    StructField("http_status", LongType()),
    StructField("card_text", StringType()),
    StructField("truncated", BooleanType()),
    StructField("fetched_at", StringType()),
])
