"""
test_io_utils.py — checks writing, appending, and reading JSONL files.

Imports / uses: datatrust/io_utils.py
Used by: pytest
"""

from datatrust.io_utils import append_jsonl, read_jsonl, write_jsonl


def test_write_then_read(tmp_path):
    path = tmp_path / "out.jsonl"
    write_jsonl([{"a": 1}, {"a": 2}], path)
    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]


def test_append_adds_lines(tmp_path):
    path = tmp_path / "out.jsonl"
    append_jsonl({"a": 1}, path)
    append_jsonl({"a": 2}, path)
    assert len(read_jsonl(path)) == 2


def test_read_skips_broken_last_line(tmp_path):
    # Simulates a crash in the middle of writing a line.
    path = tmp_path / "out.jsonl"
    path.write_text('{"a": 1}\n{"a": 2', encoding="utf-8")
    assert read_jsonl(path) == [{"a": 1}]


def test_read_missing_file_returns_empty(tmp_path):
    assert read_jsonl(tmp_path / "nope.jsonl") == []


def test_non_english_text_survives(tmp_path):
    path = tmp_path / "out.jsonl"
    write_jsonl([{"text": "日本語 – café"}], path)
    assert read_jsonl(path)[0]["text"] == "日本語 – café"
