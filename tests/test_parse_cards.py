"""
test_parse_cards.py — checks that README cards are split into the right sections.

Imports / uses: datatrust/pipelines/parse_cards.py, configs/card_sections.yaml
Used by: pytest
"""

import pytest

from datatrust.pipelines.parse_cards import (
    has_real_content,
    load_section_keywords,
    normalize_heading,
    parse_card,
    section_for_heading,
    split_front_matter,
    split_into_sections,
)

FILLER = "This section has enough real words to count as content."

# A small card shaped like HF's official template.
SAMPLE_CARD = f"""---
license: mit
language:
- en
---
# Dataset Card for Tiny

## Dataset Description

### Dataset Summary
{FILLER}

## Dataset Structure

### Data Fields
[More Information Needed]

## Dataset Creation

### Source Data
Built from the squad dataset. {FILLER}

## Considerations for Using the Data
[More Information Needed]

### Licensing Information
MIT

### Citation Information
```bibtex
@article{{tiny2024, title={{Tiny}}}}
```
"""


# Loads the real card_sections.yaml once for all tests in this file.
@pytest.fixture(scope="module")
def keywords():
    return load_section_keywords()


def test_split_front_matter():
    front_matter, body = split_front_matter("---\nlicense: mit\n---\n# Title\ntext")
    assert front_matter == "license: mit"
    assert body == "# Title\ntext"


def test_no_front_matter():
    front_matter, body = split_front_matter("# Title\ntext")
    assert front_matter is None
    assert body == "# Title\ntext"


def test_unclosed_front_matter_is_kept_as_text():
    front_matter, body = split_front_matter("---\nlicense: mit\n# Title")
    assert front_matter is None
    assert "# Title" in body


def test_none_card_is_safe(keywords):
    result = parse_card(None, keywords)
    assert result["sections_found"] == []
    assert result["word_count"] == 0


def test_code_comments_are_not_headings():
    body = "## Usage\n```python\n# load the data\nimport datasets\n```\n## Citation\nx"
    headings = [heading for heading, _ in split_into_sections(body)]
    assert headings == ["Usage", "Citation"]


def test_normalize_heading_removes_emoji_numbers_punctuation():
    assert normalize_heading("📚 1. Citation Information:") == "citation information"


def test_section_for_heading(keywords):
    assert section_for_heading("Licensing Information", keywords) == "license"
    assert section_for_heading("Bias, Risks, and Limitations", keywords) == "limitations"
    assert section_for_heading("Source Data", keywords) == "sources"
    assert section_for_heading("How to use", keywords) == "uses"
    assert section_for_heading("Data Fields", keywords) == "structure"
    assert section_for_heading("Dataset Summary", keywords) == "description"
    assert section_for_heading("Contributions", keywords) is None


def test_word_boundaries_prevent_false_matches(keywords):
    # "because" contains "use" but is not the word "use".
    assert section_for_heading("Because reasons", keywords) is None


def test_placeholder_is_not_real_content():
    assert has_real_content("[More Information Needed]") is False
    assert has_real_content("[More Information Needed].") is False
    assert has_real_content("TBD") is False
    assert has_real_content("   ") is False
    assert has_real_content(FILLER) is True


def test_short_real_answer_counts():
    # A License section that only says "MIT" is a real, complete answer.
    assert has_real_content("MIT") is True


def test_parse_sample_card(keywords):
    result = parse_card(SAMPLE_CARD, keywords)
    assert result["has_front_matter"] is True
    assert result["sections_found"] == ["citation", "description", "license", "sources"]
    # These two only contain the template placeholder.
    assert result["empty_sections"] == ["limitations", "structure"]
    assert "squad" in result["section_texts"]["sources"]


def test_section_filled_under_another_heading_is_not_empty(keywords):
    card = f"## Dataset Creation\n\n### Source Data\n{FILLER}"
    result = parse_card(card, keywords)
    assert result["sections_found"] == ["sources"]
    assert result["empty_sections"] == []


def test_two_headings_join_into_one_section(keywords):
    card = f"## Source Data\nFirst part. {FILLER}\n## Provenance\nSecond part. {FILLER}"
    text = parse_card(card, keywords)["section_texts"]["sources"]
    assert "First part" in text and "Second part" in text
