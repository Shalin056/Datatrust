"""
fetch_cards.py — downloads each dataset's README "card" (the page that explains the dataset).
Saves after EVERY card, so if the run stops halfway, the next run continues where it left off.

Imports / uses: datatrust/collector/hf_client.py, datatrust/io_utils.py,
                datatrust/collector/fetch_datasets.py (now_utc_text), datatrust/logging_setup.py
Used by: datatrust/collector/run_collect.py
"""

from datatrust.collector.fetch_datasets import now_utc_text
from datatrust.collector.hf_client import HFClientError
from datatrust.io_utils import append_jsonl, read_jsonl
from datatrust.logging_setup import get_logger

logger = get_logger("fetch_cards")

CARD_URL = "https://huggingface.co/datasets/{dataset_id}/resolve/main/README.md"
LOG_EVERY = 100


# Downloads one dataset card and describes what happened.
# Inputs: client — an HFClient; dataset_id — like "squad"; max_chars — length limit.
# Returns: dict with dataset_id, status ("ok", "missing", "no_access", "error"),
#          http_status, card_text (or None), truncated (True/False), fetched_at.
def fetch_card(client, dataset_id, max_chars=200000):
    url = CARD_URL.format(dataset_id=dataset_id)
    try:
        http_status, card_text = client.get_text(url)
    except HFClientError as error:
        # Even after retries it failed: record it and move on, don't stop the whole run.
        logger.warning(f"Could not fetch card for {dataset_id}: {error}")
        http_status, card_text = None, None

    truncated = False
    if card_text is not None and len(card_text) > max_chars:
        card_text = card_text[:max_chars]
        truncated = True

    return {
        "dataset_id": dataset_id,
        "status": card_status(http_status),
        "http_status": http_status,
        "card_text": card_text,
        "truncated": truncated,
        "fetched_at": now_utc_text(),
    }


# Translates an HTTP status code into a simple word.
# Inputs: http_status — number like 200 or 404, or None if the request failed completely.
# Returns: "ok", "missing" (no README), "no_access" (gated/private), or "error".
def card_status(http_status):
    if http_status == 200:
        return "ok"
    if http_status == 404:
        return "missing"
    # HF answers 401/403 for gated datasets, and 401 for unknown repos without a token.
    if http_status in (401, 403):
        return "no_access"
    return "error"


# Reads the cards file and lists which datasets are already done (for resuming).
# Cards that ended in "error" are NOT counted as done, so they get retried next run.
# Inputs: cards_path — path to cards.jsonl.
# Returns: set of dataset_id strings.
def load_done_ids(cards_path):
    return {row["dataset_id"] for row in read_jsonl(cards_path) if row.get("status") != "error"}


# Downloads cards for many datasets, appending each result to cards_path.
# Inputs: client — an HFClient; dataset_ids — list of ids; cards_path — output file;
#         max_chars — card length limit.
# Returns: dict counting results, e.g. {"ok": 950, "missing": 40, "skipped": 0, ...}.
def fetch_all_cards(client, dataset_ids, cards_path, max_chars=200000):
    done_ids = load_done_ids(cards_path)
    counts = {"ok": 0, "missing": 0, "no_access": 0, "error": 0, "skipped": 0}
    todo = [dataset_id for dataset_id in dataset_ids if dataset_id not in done_ids]
    counts["skipped"] = len(dataset_ids) - len(todo)
    if counts["skipped"]:
        logger.info(f"Resuming: {counts['skipped']} cards already saved, {len(todo)} to go")

    for number, dataset_id in enumerate(todo, start=1):
        card = fetch_card(client, dataset_id, max_chars)
        append_jsonl(card, cards_path)
        counts[card["status"]] += 1
        if number % LOG_EVERY == 0:
            logger.info(f"Cards: {number}/{len(todo)} done")

    logger.info(f"Cards finished: {counts}")
    return counts
