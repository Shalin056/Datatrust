"""
test_fetch_cards.py — checks card downloading, status labels, truncation, and resuming.

Imports / uses: datatrust/collector/fetch_cards.py, datatrust/collector/hf_client.py,
                datatrust/io_utils.py, tests/conftest.py
Used by: pytest
"""

from datatrust.collector.fetch_cards import card_status, fetch_all_cards, fetch_card
from datatrust.collector.hf_client import HFClient
from datatrust.io_utils import read_jsonl
from tests.conftest import FakeResponse, FakeSession


def test_card_status_labels():
    assert card_status(200) == "ok"
    assert card_status(404) == "missing"
    assert card_status(401) == "no_access"
    assert card_status(403) == "no_access"
    assert card_status(None) == "error"


def test_fetch_card_ok():
    session = FakeSession([FakeResponse(200, text="---\nlicense: mit\n---\n# Hello")])
    card = fetch_card(HFClient(session=session), "user/data")
    assert card["status"] == "ok"
    assert card["card_text"].startswith("---")
    assert card["truncated"] is False
    assert session.calls[0]["url"].endswith("/datasets/user/data/resolve/main/README.md")


def test_fetch_card_truncates_long_text():
    session = FakeSession([FakeResponse(200, text="x" * 50)])
    card = fetch_card(HFClient(session=session), "user/data", max_chars=10)
    assert len(card["card_text"]) == 10
    assert card["truncated"] is True


def test_fetch_card_records_error_instead_of_crashing(no_sleep):
    session = FakeSession([FakeResponse(500)] * 2)
    card = fetch_card(HFClient(max_retries=2, session=session), "user/data")
    assert card["status"] == "error"
    assert card["card_text"] is None


def test_fetch_all_cards_resumes_and_retries_errors(tmp_path):
    cards_path = tmp_path / "cards.jsonl"
    # First run: "a" works, "b" is missing.
    session = FakeSession([FakeResponse(200, text="A"), FakeResponse(404)])
    fetch_all_cards(HFClient(session=session), ["a", "b"], cards_path)

    # Second run with one more dataset: only "c" should be downloaded.
    session = FakeSession([FakeResponse(200, text="C")])
    counts = fetch_all_cards(HFClient(session=session), ["a", "b", "c"], cards_path)
    assert counts["skipped"] == 2
    assert counts["ok"] == 1
    assert len(session.calls) == 1
    assert [row["dataset_id"] for row in read_jsonl(cards_path)] == ["a", "b", "c"]
