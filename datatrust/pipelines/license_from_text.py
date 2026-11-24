"""
license_from_text.py — finds the license a dataset states in its README "License" section,
for datasets that have NO license tag. Example: "released under the **Apache-2.0 License**"
becomes the license ID "apache-2.0".

It also notices four kinds of phrases that change the meaning of the section:
  mixed      "each sub-dataset keeps its own license"  -> needs a human ("other")
  restricted "All Rights Reserved", "academic use only" -> needs a human ("other")
  custom     "Skywork Community License", "terms of use" -> needs a human ("other")
  none       "Not specified. No licence has been chosen" -> no license at all

This file is plain Python (no Spark), so it is easy to test on Windows.

Imports / uses: configs/license_aliases.yaml, PyYAML, datatrust/config.py (PROJECT_ROOT),
                datatrust/pipelines/normalize_license.py (load_license_table, to check IDs)
Used by: datatrust/pipelines/clean_metadata.py (Step 4.5), tests/test_license_from_text.py
"""

import re

import yaml

from datatrust.config import PROJECT_ROOT
from datatrust.pipelines.normalize_license import load_license_table

ALIASES_FILE = PROJECT_ROOT / "configs" / "license_aliases.yaml"

# A sentence that starts like this talks about the CODE, not the data
# ("Our code is released under Apache 2.0"), so its license must not count for the dataset.
CODE_SENTENCE = re.compile(r"^(the |our )?(code|evaluation harness|harness|tooling|software)\b")

# Shown as the license detail when one of the signals is found.
# Checked in this order: the first signal found decides the detail text.
SIGNAL_DETAILS = {
    "mixed": "mixed: parts of the dataset keep their own licenses",
    "restricted": "restricted: the card limits how the data may be used",
    "custom": "custom: the card uses its own license or extra terms",
}
UNRECOGNISED_DETAIL = "license described in the card but not recognised"
# A License section naming this many different licenses describes a compilation of
# datasets (real example: BAAI/CCI4.0 lists 8), not one license for the whole dataset.
MIXED_LICENSE_COUNT = 3


# Makes text easy to compare: lowercase, every symbol becomes a space, single spaces.
# "CC BY-NC-SA 4.0!" -> "cc by nc sa 4 0"
# Inputs: text — any text (may be None).
# Returns: cleaned text ("" for None).
def normalize_text(text):
    cleaned = re.sub(r"[^a-z0-9]", " ", (text or "").lower())
    return " ".join(cleaned.split())


# Reads configs/license_aliases.yaml, cleans every alias the same way as the card text,
# and checks every license ID exists in configs/licenses.yaml (a typo would silently never match).
# Inputs: path — the aliases file; license_table — from load_license_table() (loaded if None).
# Returns: dict with
#   "aliases": list of (alias_text, license_id), LONGEST alias first
#   "signals": dict like {"mixed": ["its own license", ...], "restricted": [...], "none": [...]}
def load_license_rules(path=ALIASES_FILE, license_table=None):
    with open(path, encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    if license_table is None:
        license_table = load_license_table()

    aliases = []
    for license_id, names in raw["aliases"].items():
        if license_id not in license_table:
            raise ValueError(f"{license_id!r} in {path} is not in configs/licenses.yaml")
        for name in names:
            aliases.append((normalize_text(name), license_id))
    # Longest first, so "cc by nc 4 0" is matched before the shorter "cc by 4 0" could be.
    aliases.sort(key=lambda pair: len(pair[0]), reverse=True)

    signals = {
        name: [normalize_text(phrase) for phrase in phrases]
        for name, phrases in raw["signals"].items()
    }
    return {"aliases": aliases, "signals": signals}


# Splits text into sentences (at ". ", "! ", "? " and line breaks).
# Inputs: text — the License section text.
# Returns: list of sentences (not cleaned yet).
def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [part for part in parts if part.strip()]


# Removes sentences about the code and joins the rest into one cleaned text.
# Inputs: text — the License section text.
# Returns: cleaned text with only the sentences that can describe the DATA's license.
def data_sentences_text(text):
    # Hidden HTML comments (<!-- ... -->) are template notes, not the authors' statement.
    visible = re.sub(r"<!--.*?-->", " ", text or "", flags=re.DOTALL)
    kept = []
    for sentence in split_sentences(visible):
        cleaned = normalize_text(sentence)
        if cleaned and not CODE_SENTENCE.match(cleaned):
            kept.append(cleaned)
    return " ".join(kept)


# Finds every license ID mentioned in cleaned text.
# Each match is blanked out after it is found, so a shorter alias inside a longer one
# ("cc by 4 0" inside "cc by nc 4 0") cannot be counted a second time.
# Inputs: cleaned_text — from data_sentences_text(); aliases — list from load_license_rules().
# Returns: sorted list of license IDs (may be empty).
def find_license_ids(cleaned_text, aliases):
    # Spaces at both ends let every alias be matched with spaces around it (whole words).
    remaining = f" {cleaned_text} "
    found = set()
    for alias, license_id in aliases:
        target = f" {alias} "
        if target in remaining:
            found.add(license_id)
            # Keep one space on each side so neighbouring words stay separated.
            remaining = remaining.replace(target, " " * len(target))
    return sorted(found)


# Finds which signals (mixed / restricted / none) appear in cleaned text.
# Inputs: cleaned_text — from data_sentences_text(); signals — dict from load_license_rules().
# Returns: dict signal name -> first phrase found, e.g. {"restricted": "all rights reserved"}.
def find_signals(cleaned_text, signals):
    padded = f" {cleaned_text} "
    found = {}
    for name, phrases in signals.items():
        for phrase in phrases:
            if f" {phrase} " in padded:
                found[name] = phrase
                break
    return found


# The main function: reads one License section.
# Inputs: section_text — text of the card's License section (or None); rules — from
#         load_license_rules().
# Returns: dict with
#   license_ids  sorted list of IDs; "other" means a human must read the card
#   detail       short explanation for "other" (or None)
def licenses_from_text(section_text, rules):
    cleaned = data_sentences_text(section_text)
    if not cleaned:
        return {"license_ids": [], "detail": None}

    license_ids = find_license_ids(cleaned, rules["aliases"])
    signals = find_signals(cleaned, rules["signals"])

    # "Not specified" with no license named = the dataset really has no license.
    if "none" in signals and not license_ids:
        return {"license_ids": [], "detail": None}

    if len(license_ids) >= MIXED_LICENSE_COUNT:
        signals.setdefault("mixed", "many licenses listed")

    for signal in SIGNAL_DETAILS:
        if signal in signals:
            ids = sorted(set(license_ids) | {"other"})
            return {"license_ids": ids, "detail": SIGNAL_DETAILS[signal]}

    # The authors wrote something about licensing, but we could not recognise it
    # (e.g. "NVIDIA License", "See LICENSE.txt"). A human must read it.
    if not license_ids:
        return {"license_ids": ["other"], "detail": UNRECOGNISED_DETAIL}

    return {"license_ids": license_ids, "detail": None}


# Decides which license information to trust for one dataset.
# Tags win, because HF checks them against its official list; card text is only
# used when there are no tags at all.
# Inputs: tag_licenses — list from the "license:..." tags; text_result — from licenses_from_text().
# Returns: (license_ids, license_source, detail)
#          license_source is "tag", "card_text" or "none".
def choose_license_source(tag_licenses, text_result):
    if tag_licenses:
        return list(tag_licenses), "tag", None
    if text_result["license_ids"]:
        return text_result["license_ids"], "card_text", text_result["detail"]
    return [], "none", None
