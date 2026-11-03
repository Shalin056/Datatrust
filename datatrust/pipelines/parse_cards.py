"""
parse_cards.py — reads a dataset's README ("card") and works out which important sections
it has: description, structure, uses, sources, limitations, license, citation.
A section only counts if it has REAL content under it, not an empty template placeholder.

This file is plain Python (no Spark), so it is easy to test on Windows.
The Spark cleaning job (Step 4.5) calls parse_card() for every card.

Imports / uses: configs/card_sections.yaml, PyYAML, datatrust/config.py (PROJECT_ROOT)
Used by: datatrust/pipelines/clean_metadata.py (Step 4.5), tests/test_parse_cards.py
"""

import re

import yaml

from datatrust.config import PROJECT_ROOT

SECTIONS_FILE = PROJECT_ROOT / "configs" / "card_sections.yaml"

# Filler text that means "nobody wrote this section". The first one is what HF's card
# template puts in every empty section (198 of our real cards still contain it).
PLACEHOLDERS = ["[more information needed]", "tbd", "todo", "n/a", "coming soon"]
# After removing filler, a section needs at least this many characters to count.
# Kept small on purpose: a License section that just says "MIT" is a real answer.
MIN_SECTION_CHARS = 3

# A Markdown heading: 1–6 "#" signs, a space, then the heading text.
# Example match: "## Dataset Summary" -> level "##", text "Dataset Summary".
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


# Reads configs/card_sections.yaml.
# Inputs: path — the YAML file (defaults to configs/card_sections.yaml).
# Returns: dict like {"license": ["license", "licence", ...], "citation": [...], ...}
#          in the same order as the file (Python dicts keep insertion order).
def load_section_keywords(path=SECTIONS_FILE):
    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file)["sections"]


# Separates the YAML header (between the first two "---" lines) from the rest of the card.
# Inputs: card_text — the whole README text (may be None).
# Returns: (front_matter, body). front_matter is None if the card has no header.
def split_front_matter(card_text):
    text = card_text or ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    # Find the closing "---", starting from the second line.
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            front_matter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1:])
            return front_matter, body
    # Opening "---" but no closing one: treat the whole thing as normal text.
    return None, text


# Splits the card body into sections, one per heading.
# Lines inside ``` code blocks are never treated as headings, because "# comment" lines
# in code examples look exactly like headings (647 of our real cards have them).
# Inputs: body — card text without the YAML header.
# Returns: list of (heading_text, section_text) pairs, in order.
def split_into_sections(body):
    sections = []
    current_heading = None
    current_lines = []
    in_code_block = False

    for line in body.splitlines():
        stripped = line.strip()
        # ``` or ~~~ opens or closes a code block.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block

        match = None if in_code_block else HEADING_PATTERN.match(stripped)
        if match:
            # Save the section we were collecting, then start a new one.
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = match.group(2)
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_lines)))
    return sections


# Makes a heading easy to compare: lowercase letters and single spaces only.
# "## 📚 1. Citation Information:" -> "citation information"
# Inputs: heading — raw heading text.
# Returns: cleaned text.
def normalize_heading(heading):
    text = heading.lower()
    # Remove Markdown links and formatting characters, keep the words.
    text = re.sub(r"[^a-z\s]", " ", text)
    return " ".join(text.split())


# Finds which section a heading belongs to.
# Inputs: heading — raw heading text; keywords — from load_section_keywords().
# Returns: section name like "citation", or None if it matches nothing.
def section_for_heading(heading, keywords):
    cleaned = normalize_heading(heading)
    for section_name, words in keywords.items():
        for word in words:
            # \b = word boundary, so "use" matches "how to use" but not "because".
            if re.search(rf"\b{re.escape(word)}\b", cleaned):
                return section_name
    return None


# Decides if a section has real content (not empty, not just filler like "TBD").
# Inputs: text — the text under one heading.
# Returns: True or False.
def has_real_content(text):
    cleaned = (text or "").lower()
    for placeholder in PLACEHOLDERS:
        cleaned = cleaned.replace(placeholder, "")
    # Ignore leftover punctuation/spaces, e.g. "[More Information Needed]." leaves ".".
    letters_and_digits = re.sub(r"[^a-z0-9]", "", cleaned)
    return len(letters_and_digits) >= MIN_SECTION_CHARS


# The main function: analyses one card.
# Inputs: card_text — the whole README text (may be None); keywords — from
#         load_section_keywords().
# Returns: dict with
#   has_front_matter   True if the card starts with a YAML header
#   word_count         number of words in the body (rough size of the documentation)
#   sections_found     sorted list of section names with real content, e.g. ["citation", ...]
#   section_texts      dict section name -> its text (several headings are joined together)
#   empty_sections     sorted list of sections that exist but were left empty/placeholder
def parse_card(card_text, keywords):
    front_matter, body = split_front_matter(card_text)
    section_texts = {}
    empty_sections = set()

    for heading, text in split_into_sections(body):
        section_name = section_for_heading(heading, keywords)
        if section_name is None:
            continue
        if has_real_content(text):
            # Several headings can map to one section (e.g. "Source Data" and
            # "Dataset Creation" are both "sources"), so we join their texts.
            previous = section_texts.get(section_name, "")
            section_texts[section_name] = (previous + "\n" + text).strip()
        else:
            empty_sections.add(section_name)

    # A section that is empty under one heading but filled under another is NOT empty.
    empty_sections -= set(section_texts)

    return {
        "has_front_matter": front_matter is not None,
        "word_count": len(body.split()),
        "sections_found": sorted(section_texts),
        "section_texts": section_texts,
        "empty_sections": sorted(empty_sections),
    }
