"""
test_clean_rules.py — checks that one dataset's raw fields become the right clean fields.

Imports / uses: datatrust/pipelines/clean_rules.py (and through it the license and card rules)
Used by: pytest
"""

import json

import pytest

from datatrust.pipelines.clean_rules import (
    MAX_SECTION_CHARS,
    build_clean_fields,
    load_all_rules,
    not_a_dataset_reasons,
    parse_card_data,
    shorten,
    source_datasets_from,
    tag_values,
)

CARD = """---
license: mit
---
# Dataset Card for Tiny

## Dataset Summary
A tiny dataset of questions used only for tests.

## Source Data
Built from rajpurkar/squad by keeping short questions.

## License
Released under the **Apache-2.0 License**.
"""


# Loads every rule file once for all tests in this file.
@pytest.fixture(scope="module")
def rules():
    return load_all_rules()


def test_tag_values():
    tags = ["language:en", "language:fr", "modality:text", "license:mit"]
    assert tag_values(tags, "language") == ["en", "fr"]
    assert tag_values(tags, "arxiv") == []
    assert tag_values(None, "language") == []


def test_parse_card_data_handles_bad_input():
    assert parse_card_data('{"license": "mit"}') == {"license": "mit"}
    assert parse_card_data(None) == {}
    assert parse_card_data("not json {") == {}
    assert parse_card_data('["a list", "not a dict"]') == {}


def test_source_datasets_from():
    assert source_datasets_from({"source_datasets": ["extended|squad"]}) == ["extended|squad"]
    assert source_datasets_from({"source_datasets": "original"}) == ["original"]
    assert source_datasets_from({}) == []


def test_shorten():
    assert shorten(None) is None
    assert len(shorten("x" * (MAX_SECTION_CHARS + 50))) == MAX_SECTION_CHARS


def test_tagged_dataset_with_card(rules):
    card_data = json.dumps({"license": "mit", "source_datasets": ["extended|squad"]})
    tags = ["language:en", "size_categories:1K<n<10K", "license:mit", "arxiv:1606.05250"]
    row = build_clean_fields(tags, ["mit"], card_data, CARD, "ok", rules)

    assert row["languages"] == ["en"]
    assert row["size_category"] == "1K<n<10K"
    assert row["arxiv_ids"] == ["1606.05250"]
    assert row["source_datasets"] == ["extended|squad"]
    # Tags win: the README says Apache-2.0, but the tag says MIT.
    assert row["license_ids"] == ["mit"]
    assert row["license_source"] == "tag"
    assert row["license_category"] == "permissive"
    assert row["has_card"] is True
    assert row["sections_found"] == ["description", "license", "sources"]
    assert "rajpurkar/squad" in row["sources_text"]


def test_untagged_dataset_uses_card_text(rules):
    row = build_clean_fields([], [], None, CARD, "ok", rules)
    assert row["license_ids"] == ["apache-2.0"]
    assert row["license_source"] == "card_text"
    assert row["license_category"] == "permissive"


def test_dataset_without_card(rules):
    row = build_clean_fields(["modality:image"], [], None, None, "missing", rules)
    assert row["has_card"] is False
    assert row["card_word_count"] == 0
    assert row["sections_found"] == []
    assert row["license_source"] == "none"
    assert row["license_category"] == "missing"
    assert row["modalities"] == ["image"]
    assert row["size_category"] is None


def test_card_text_ignored_when_status_is_not_ok(rules):
    # A failed download must never be parsed as if it were a README.
    row = build_clean_fields([], [], None, CARD, "error", rules)
    assert row["has_card"] is False
    assert row["license_source"] == "none"


def test_other_license_keeps_its_name(rules):
    card_data = json.dumps({"license": "other", "license_name": "bedlam-non-commercial"})
    row = build_clean_fields(["license:other"], ["other"], card_data, None, "missing", rules)
    assert row["license_category"] == "custom"
    assert row["license_detail"] == "bedlam-non-commercial"


def test_documented_repo_is_never_flagged():
    assert not_a_dataset_reasons(True, [], True) == []


def test_undocumented_but_loadable_repo_is_not_flagged():
    # Real case: some undocumented repos hold real data that HF can load.
    assert not_a_dataset_reasons(False, ["library:datasets", "modality:text"], False) == []


def test_undocumented_file_pile_is_flagged():
    assert not_a_dataset_reasons(False, [], False) == ["not_loadable"]


def test_bulk_uploader_is_flagged_even_if_loadable():
    # Real case: icdn10/content-2026... image hosting repos are loadable image folders.
    tags = ["library:datasets", "format:imagefolder"]
    assert not_a_dataset_reasons(False, tags, True) == ["bulk_uploader"]
    assert not_a_dataset_reasons(False, None, True) == ["not_loadable", "bulk_uploader"]
