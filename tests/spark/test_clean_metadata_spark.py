"""
test_clean_metadata_spark.py — runs the real Spark cleaning job on a tiny, hand-made dataset
and checks the clean table. These are the project's first tests that start Spark.

Run inside Docker (PySpark lives only there):
  docker compose run --rm pipeline pytest tests/spark -v
On Windows they are skipped automatically.

Imports / uses: datatrust/pipelines/clean_metadata.py, spark_session.py, clean_rules.py, pyspark
Used by: pytest
"""

import json

import pytest

# Skip this whole file when PySpark is not installed (the Windows .venv).
pytest.importorskip("pyspark")

from datatrust.pipelines.clean_metadata import (  # noqa: E402 (must come after the skip check)
    add_clean_fields,
    add_not_a_dataset_flag,
    check_quality,
    join_cards,
    read_raw,
    select_final_columns,
)
from datatrust.pipelines.clean_rules import BULK_UPLOAD_MIN_REPOS, load_all_rules  # noqa: E402
from datatrust.pipelines.spark_session import create_spark  # noqa: E402

COLLECTED_AT = "2026-10-18T12:00:00+00:00"
GOOD_CARD = "---\nlicense: mit\n---\n## Dataset Summary\nA small real dataset for tests.\n"


# Builds one raw dataset record shaped like the collector's output (fetch_datasets.py).
# Inputs: dataset_id; author; tags; last_modified (ISO text).
# Returns: dict ready to be written as one JSONL line.
def raw_dataset(dataset_id, author, tags, last_modified="2026-10-08T12:00:00.000Z"):
    licenses = [tag.split(":", 1)[1] for tag in tags if tag.startswith("license:")]
    return {
        "dataset_id": dataset_id,
        "author": author,
        "license_from_tags": licenses,
        "license_from_card": None,
        "tags": tags,
        "downloads": 10,
        "likes": 1,
        "created_at": "2024-01-01T00:00:00.000Z",
        "last_modified": last_modified,
        "gated": False,
        "private": False,
        "disabled": False,
        "description": None,
        "card_data": {"license": licenses[0]} if licenses else {},
        "collected_at": COLLECTED_AT,
    }


# Builds one raw card record shaped like fetch_cards.py's output.
# Inputs: dataset_id; card_text (None = no README).
# Returns: dict ready to be written as one JSONL line.
def raw_card(dataset_id, card_text):
    return {
        "dataset_id": dataset_id,
        "status": "ok" if card_text else "missing",
        "http_status": 200 if card_text else 404,
        "card_text": card_text,
        "truncated": False,
        "fetched_at": COLLECTED_AT,
    }


# Writes a list of dicts as a JSONL file.
def write_jsonl(rows, path):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


# One Spark session shared by every test in this file (starting Spark takes a few seconds).
@pytest.fixture(scope="module")
def spark():
    session = create_spark("tests")
    yield session
    session.stop()


# A tiny raw folder with four kinds of repos, and the clean table built from it:
#   good/real        documented dataset, MIT, updated 10 days before collection
#   lonely/ecg       no README but loadable -> NOT flagged (maybe real, just undocumented)
#   dump/dump        no README, not loadable -> flagged "not_loadable"
#   cdn/content-N    bulk uploader: 10 loadable repos, none documented -> flagged "bulk_uploader"
@pytest.fixture(scope="module")
def clean_rows(spark, tmp_path_factory):
    raw_dir = tmp_path_factory.mktemp("raw")
    datasets = [
        raw_dataset("good/real", "good", ["license:mit", "library:datasets", "language:en"]),
        raw_dataset("lonely/ecg", "lonely", ["library:datasets"]),
        raw_dataset("dump/dump", "dump", [], last_modified="2024-10-18T12:00:00.000Z"),
    ]
    datasets += [
        raw_dataset(f"cdn/content-{number}", "cdn", ["library:datasets", "format:imagefolder"])
        for number in range(BULK_UPLOAD_MIN_REPOS)
    ]
    cards = [raw_card("good/real", GOOD_CARD)]
    cards += [raw_card(row["dataset_id"], None) for row in datasets[1:]]
    write_jsonl(datasets, raw_dir / "datasets.jsonl")
    write_jsonl(cards, raw_dir / "cards.jsonl")

    raw_datasets, raw_cards = read_raw(spark, raw_dir)
    clean = select_final_columns(
        add_clean_fields(join_cards(raw_datasets, raw_cards), load_all_rules())
    )
    clean = add_not_a_dataset_flag(clean)
    check_quality(clean, expected_rows=len(datasets))
    # collect() brings the rows back to plain Python so the tests can look at them.
    return {row["dataset_id"]: row.asDict() for row in clean.collect()}


def test_one_row_per_dataset(clean_rows):
    assert len(clean_rows) == 3 + BULK_UPLOAD_MIN_REPOS


def test_documented_dataset_is_cleaned(clean_rows):
    row = clean_rows["good/real"]
    assert row["dataset_name"] == "real"
    assert row["license_category"] == "permissive"
    assert row["license_source"] == "tag"
    assert row["languages"] == ["en"]
    assert row["has_card"] is True
    assert row["sections_found"] == ["description"]
    assert row["days_since_update"] == 10
    assert row["likely_not_a_dataset"] is False


def test_undocumented_but_loadable_is_not_flagged(clean_rows):
    row = clean_rows["lonely/ecg"]
    assert row["has_card"] is False
    assert row["likely_not_a_dataset"] is False


def test_file_dump_is_flagged(clean_rows):
    row = clean_rows["dump/dump"]
    assert row["likely_not_a_dataset"] is True
    assert row["not_a_dataset_reasons"] == ["not_loadable"]
    assert row["days_since_update"] == 730


def test_bulk_uploader_is_flagged(clean_rows):
    row = clean_rows["cdn/content-0"]
    assert row["likely_not_a_dataset"] is True
    assert row["not_a_dataset_reasons"] == ["bulk_uploader"]


def test_quality_check_catches_duplicates(spark):
    duplicated = spark.createDataFrame([("a/x",), ("a/x",)], ["dataset_id"])
    with pytest.raises(ValueError, match="more than once"):
        check_quality(duplicated, expected_rows=2)


def test_quality_check_catches_lost_rows(spark):
    one_row = spark.createDataFrame([("a/x",)], ["dataset_id"])
    with pytest.raises(ValueError, match="Expected 2 rows"):
        check_quality(one_row, expected_rows=2)
