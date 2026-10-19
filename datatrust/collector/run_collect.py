"""
run_collect.py — the command you run to do the whole collection step:
  1) download dataset metadata  -> data/raw/datasets.jsonl
  2) download dataset cards     -> data/raw/cards.jsonl

Run from the project folder:
  python -m datatrust.collector.run_collect --limit 50

Imports / uses: datatrust/config.py, datatrust/io_utils.py, datatrust/logging_setup.py,
                datatrust/collector/hf_client.py, fetch_datasets.py, fetch_cards.py
Used by: you (command line), and later .github/workflows/refresh_data.yml
"""

import argparse
import sys

from datatrust.collector.fetch_cards import fetch_all_cards
from datatrust.collector.fetch_datasets import fetch_dataset_list
from datatrust.collector.hf_client import HFClient, HFClientError
from datatrust.config import load_settings, project_path
from datatrust.io_utils import write_jsonl
from datatrust.logging_setup import get_logger

logger = get_logger("run_collect")


# Reads command-line options like --limit 50.
# Inputs: argv — list of words typed after the command (None = use the real command line).
# Returns: an object with .limit, .skip_cards and .fresh.
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Collect dataset data from Hugging Face.")
    parser.add_argument("--limit", type=int, help="How many datasets to collect")
    parser.add_argument("--skip-cards", action="store_true", help="Only fetch metadata, no cards")
    parser.add_argument("--fresh", action="store_true", help="Delete saved cards and start over")
    return parser.parse_args(argv)


# Runs the full collection step.
# Inputs: argv — optional list of command-line words (used by tests).
# Returns: 0 if it worked, 1 if it failed (the usual "exit code" convention).
def main(argv=None):
    args = parse_args(argv)
    settings = load_settings()
    collect = settings["collect"]
    max_datasets = args.limit or collect["max_datasets"]

    if not settings["hf_token"]:
        logger.warning("No HF_TOKEN found in .env, so rate limits will be lower. Continuing.")

    client = HFClient(
        token=settings["hf_token"],
        timeout=settings["http"]["timeout_seconds"],
        max_retries=settings["http"]["max_retries"],
    )
    raw_dir = project_path(settings["paths"]["raw_dir"])
    datasets_path = raw_dir / "datasets.jsonl"
    cards_path = raw_dir / "cards.jsonl"

    # Step 1: metadata. If this fails we stop, because cards depend on the list of ids.
    logger.info(f"Collecting metadata for up to {max_datasets} datasets")
    try:
        records = fetch_dataset_list(client, max_datasets, collect["page_size"], collect["sort_by"])
    except HFClientError as error:
        logger.error(f"Could not download the dataset list: {error}")
        return 1
    write_jsonl(records, datasets_path)
    logger.info(f"Saved {len(records)} datasets to {datasets_path}")

    if args.skip_cards:
        return 0

    # Step 2: cards (resumable).
    if args.fresh and cards_path.exists():
        cards_path.unlink()
        logger.info("Deleted old cards file (--fresh)")
    dataset_ids = [record["dataset_id"] for record in records]
    fetch_all_cards(client, dataset_ids, cards_path, collect["max_card_chars"])
    logger.info(f"Cards saved to {cards_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
