"""
fetch_datasets.py — downloads the list of datasets and their metadata
(license, tags, dates, downloads, likes, short description) from the HF API.

Imports / uses: datatrust/collector/hf_client.py, datatrust/logging_setup.py
Used by: datatrust/collector/run_collect.py
"""

from datetime import datetime, timezone

from datatrust.logging_setup import get_logger

logger = get_logger("fetch_datasets")

DATASETS_API_URL = "https://huggingface.co/api/datasets"
LOG_EVERY = 1000


# Downloads metadata for the top datasets, in the chosen sort order.
# Inputs: client — an HFClient; max_datasets — how many to collect;
#         page_size — items per API page; sort_by — e.g. "downloads".
# Returns: list of flat dicts, one per dataset (see to_record).
def fetch_dataset_list(client, max_datasets, page_size=1000, sort_by="downloads"):
    params = {
        "sort": sort_by,
        "direction": -1,  # -1 = biggest first
        "limit": min(page_size, max_datasets),
        "full": "true",  # include tags, card data, and description
    }
    collected_at = now_utc_text()
    records = []

    for item in client.get_paged_json(DATASETS_API_URL, params=params):
        records.append(to_record(item, collected_at))
        if len(records) % LOG_EVERY == 0:
            logger.info(f"Fetched {len(records)} datasets so far")
        if len(records) >= max_datasets:
            break

    logger.info(f"Fetched {len(records)} datasets in total")
    return records


# Turns one raw API item into a flat dict with only the fields we need.
# Missing fields become None instead of crashing, because many datasets leave things empty.
# Inputs: item — dict from the API; collected_at — time text to stamp on the record.
# Returns: dict with dataset_id, author, license fields, tags, counts, dates, description.
def to_record(item, collected_at):
    tags = item.get("tags") or []
    card_data = item.get("cardData") or {}
    return {
        "dataset_id": item.get("id"),
        "author": item.get("author"),
        # License can appear in two places; we keep both and decide in the cleaning step.
        "license_from_tags": license_from_tags(tags),
        "license_from_card": card_data.get("license"),
        "tags": tags,
        "downloads": item.get("downloads"),
        "likes": item.get("likes"),
        "created_at": item.get("createdAt"),
        "last_modified": item.get("lastModified"),
        "gated": item.get("gated"),
        "private": item.get("private"),
        "disabled": item.get("disabled"),
        "description": (item.get("description") or "").strip() or None,
        "card_data": card_data,
        "collected_at": collected_at,
    }


# Finds license values in the tag list. Tags look like "license:mit".
# Inputs: tags — list of tag strings.
# Returns: list of license names (can be empty, or have several if a dataset lists many).
def license_from_tags(tags):
    prefix = "license:"
    return [tag[len(prefix):] for tag in tags if tag.startswith(prefix)]


# Returns the current time in UTC as text, like "2026-10-18T12:00:00+00:00".
# Inputs: none.
# Returns: ISO-format time string.
def now_utc_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
