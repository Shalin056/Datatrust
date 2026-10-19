"""
test_fetch_datasets.py — checks that raw API items become clean flat records,
and that collection stops at the requested number of datasets.

Imports / uses: datatrust/collector/fetch_datasets.py, datatrust/collector/hf_client.py,
                tests/conftest.py, tests/fixtures/api_datasets_page.json
Used by: pytest
"""

import json
from pathlib import Path

from datatrust.collector.fetch_datasets import fetch_dataset_list, license_from_tags, to_record
from datatrust.collector.hf_client import HFClient
from tests.conftest import FakeResponse, FakeSession

FIXTURE = Path(__file__).parent / "fixtures" / "api_datasets_page.json"


# Loads the saved sample of a real HF API page.
def load_sample_page():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_to_record_reads_real_api_item():
    item = load_sample_page()[1]
    record = to_record(item, "2026-10-18T00:00:00+00:00")
    assert record["dataset_id"] == "m-a-p/FineFineWeb"
    assert record["author"] == "m-a-p"
    assert record["license_from_tags"] == ["apache-2.0"]
    assert record["license_from_card"] == "apache-2.0"
    assert record["downloads"] == 4004565
    assert record["collected_at"] == "2026-10-18T00:00:00+00:00"


def test_to_record_handles_missing_fields():
    record = to_record({"id": "someone/empty"}, "t")
    assert record["dataset_id"] == "someone/empty"
    assert record["tags"] == []
    assert record["license_from_tags"] == []
    assert record["license_from_card"] is None
    assert record["description"] is None


def test_blank_description_becomes_none():
    record = to_record({"id": "a/b", "description": "  \n\t "}, "t")
    assert record["description"] is None


def test_license_from_tags_finds_all_licenses():
    tags = ["language:en", "license:mit", "license:cc-by-4.0"]
    assert license_from_tags(tags) == ["mit", "cc-by-4.0"]


def test_fetch_stops_at_max_datasets():
    page = [{"id": f"user/data{i}"} for i in range(10)]
    session = FakeSession([FakeResponse(200, json_data=page, next_url="https://x?p=2")])
    records = fetch_dataset_list(HFClient(session=session), max_datasets=3, page_size=10)
    assert len(records) == 3
    # It should not ask for page 2, because 3 datasets were already collected.
    assert len(session.calls) == 1


def test_fetch_asks_api_for_most_downloaded_first():
    session = FakeSession([FakeResponse(200, json_data=[])])
    fetch_dataset_list(HFClient(session=session), max_datasets=5, page_size=1000)
    params = session.calls[0]["params"]
    assert params["sort"] == "downloads"
    assert params["direction"] == -1
    assert params["limit"] == 5  # never ask for more than we need
