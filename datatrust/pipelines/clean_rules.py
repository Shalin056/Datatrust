"""
clean_rules.py — the cleaning logic for ONE dataset, as plain Python (no Spark).
It combines the earlier pieces into one clean row:
  tags          -> languages, task categories, modalities, size, arXiv papers
  card header   -> source_datasets (the "built from" list, used for lineage in Step 5)
  licenses      -> normalize_license.py + license_from_text.py
  README card   -> parse_cards.py (sections, word count, key texts)
It also decides whether a repo is likely NOT a real dataset (not_a_dataset_reasons).

Keeping this separate from the Spark job means it can be tested on Windows in under a second.
The Spark job (clean_metadata.py) calls build_clean_fields() and not_a_dataset_reasons()
once per dataset.

Imports / uses: datatrust/pipelines/normalize_license.py, license_from_text.py, parse_cards.py
Used by: datatrust/pipelines/clean_metadata.py, tests/test_clean_rules.py
"""

import json

from datatrust.pipelines.license_from_text import (
    choose_license_source,
    licenses_from_text,
    load_license_rules,
)
from datatrust.pipelines.normalize_license import load_license_table, normalize_license
from datatrust.pipelines.parse_cards import load_section_keywords, parse_card

# Section texts kept in the clean table are cut to this length, so one huge README
# cannot make the table big. Step 5 only needs the start of these sections.
MAX_SECTION_CHARS = 10000

# An owner with at least this many repos in our collection, and a README on none of them,
# is a "bulk uploader" (real examples: icdn10…icdn22 and onfdata, image hosting accounts).
BULK_UPLOAD_MIN_REPOS = 10
# HF adds this tag when its "datasets" library can load the repo as a dataset.
LOADABLE_TAG = "library:datasets"


# Loads every rule file once (licenses, license aliases, card section keywords).
# Inputs: none.
# Returns: dict with "license_table", "license_rules", "section_keywords".
def load_all_rules():
    license_table = load_license_table()
    return {
        "license_table": license_table,
        "license_rules": load_license_rules(license_table=license_table),
        "section_keywords": load_section_keywords(),
    }


# Picks the values of one kind of tag. Tags look like "language:en" or "modality:text".
# Inputs: tags — list of tag strings (may be None); prefix — e.g. "language".
# Returns: list of values without the prefix, e.g. ["en", "fr"].
def tag_values(tags, prefix):
    start = prefix + ":"
    return [tag[len(start):] for tag in (tags or []) if tag.startswith(start)]


# Turns the card header (kept as JSON text by raw_schemas.py) back into a dictionary.
# Inputs: card_data_json — JSON text, or None.
# Returns: dict (empty if missing or broken, so one bad card never stops the job).
def parse_card_data(card_data_json):
    if not card_data_json:
        return {}
    try:
        value = json.loads(card_data_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


# Reads the "source_datasets" field: the datasets this one says it was built from.
# Values look like ["original"] or ["extended|squad"]; Step 5 interprets them.
# Inputs: card_data — dict from parse_card_data().
# Returns: list of text values (a single text value becomes a one-item list).
def source_datasets_from(card_data):
    value = card_data.get("source_datasets")
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


# Cuts text to MAX_SECTION_CHARS.
# Inputs: text — text or None.
# Returns: shortened text, or None.
def shorten(text):
    if text is None:
        return None
    return text[:MAX_SECTION_CHARS]


# The main function: builds all derived fields for one dataset.
# Inputs: tags — list of tags; tag_licenses — list from "license:" tags;
#         card_data_json — card header as JSON text; card_text — README text (or None);
#         card_status — "ok", "missing", ... (or None if no card row); rules — load_all_rules().
# Returns: dict whose keys match CLEAN_FIELDS_SCHEMA in clean_metadata.py.
def build_clean_fields(tags, tag_licenses, card_data_json, card_text, card_status, rules):
    card_data = parse_card_data(card_data_json)
    has_card = card_status == "ok" and bool(card_text)
    card = parse_card(card_text if has_card else None, rules["section_keywords"])

    # Licenses: tags first; README text only when there are no tags (see license_from_text.py).
    text_result = {"license_ids": [], "detail": None}
    if not tag_licenses:
        license_section = card["section_texts"].get("license")
        text_result = licenses_from_text(license_section, rules["license_rules"])
    license_ids, license_source, text_detail = choose_license_source(tag_licenses, text_result)

    # For "other" licenses, the tag route explains itself with license_name in the header;
    # the text route explains itself with the detail from license_from_text.py.
    license_name = text_detail if license_source == "card_text" else card_data.get("license_name")
    license_info = normalize_license(license_ids, license_name, rules["license_table"])

    size_values = tag_values(tags, "size_categories")
    return {
        "languages": tag_values(tags, "language"),
        "task_categories": tag_values(tags, "task_categories"),
        "modalities": tag_values(tags, "modality"),
        "size_category": size_values[0] if size_values else None,
        "arxiv_ids": tag_values(tags, "arxiv"),
        "source_datasets": source_datasets_from(card_data),
        "license_ids": license_info["license_ids"],
        "license_source": license_source,
        "license_category": license_info["license_category"],
        "license_detail": license_info["license_detail"],
        "has_multiple_licenses": license_info["has_multiple_licenses"],
        "has_card": has_card,
        "has_front_matter": card["has_front_matter"],
        "card_word_count": card["word_count"],
        "sections_found": card["sections_found"],
        "empty_sections": card["empty_sections"],
        "description_text": shorten(card["section_texts"].get("description")),
        "sources_text": shorten(card["section_texts"].get("sources")),
    }


# Decides whether a repo is probably NOT a real dataset (file hosting, model dumps, spam),
# and why. A missing README alone is not enough: some real datasets are just undocumented.
# So we also need at least one more piece of evidence:
#   not_loadable   HF cannot load it as a dataset (no "library:datasets" tag)
#   bulk_uploader  its owner uploads many repos and documents none of them
# Inputs: has_card — True if the README was downloaded; tags — list of tags;
#         is_bulk_uploader — True/False, worked out by Spark across ALL repos of the owner.
# Returns: list of reasons; an empty list means "looks like a real dataset".
def not_a_dataset_reasons(has_card, tags, is_bulk_uploader):
    if has_card:
        return []
    reasons = []
    if LOADABLE_TAG not in (tags or []):
        reasons.append("not_loadable")
    if is_bulk_uploader:
        reasons.append("bulk_uploader")
    return reasons
