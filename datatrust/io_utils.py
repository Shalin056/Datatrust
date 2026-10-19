"""
io_utils.py — small helpers to read and write JSONL files.
JSONL ("JSON Lines") = one JSON object per line. We use it for raw data because we can
add one line at a time, so a crash never loses what was already saved.

Imports / uses: Python's built-in json and pathlib
Used by: datatrust/collector/fetch_datasets.py, datatrust/collector/fetch_cards.py
"""

import json
from pathlib import Path


# Writes a list of dictionaries to a JSONL file, replacing the file if it exists.
# Inputs: records — list of dicts; path — where to save.
# Returns: the number of lines written.
def write_jsonl(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


# Adds ONE dictionary as a new line at the end of a JSONL file.
# Inputs: record — a dict; path — the file to add to (created if missing).
# Returns: nothing.
def append_jsonl(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


# Reads a JSONL file back into a list of dictionaries.
# Broken lines (for example a half-written last line after a crash) are skipped.
# Inputs: path — the file to read.
# Returns: list of dicts (empty list if the file does not exist).
def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records
