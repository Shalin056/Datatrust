"""
normalize_license.py — turns a dataset's raw license tags into one clear answer:
which licenses it uses, and which category that puts the dataset in
(permissive, non_commercial, custom, missing, ...).

This file is plain Python (no Spark), so it is easy to test on Windows.
The Spark cleaning job (Step 4.4) calls normalize_license() for every dataset.

Imports / uses: configs/licenses.yaml, PyYAML, datatrust/config.py (PROJECT_ROOT)
Used by: datatrust/pipelines/clean_metadata.py (Step 4.4), tests/test_normalize_license.py
"""

import yaml

from datatrust.config import PROJECT_ROOT

LICENSES_FILE = PROJECT_ROOT / "configs" / "licenses.yaml"

# Categories from least to most restrictive. When a dataset lists several licenses,
# we report the most restrictive one (see pick_strictest_category for why).
# "missing" = the dataset gave no license at all.
CATEGORY_ORDER = [
    "public_domain",
    "permissive",
    "restricted_use",
    "share_alike",
    "non_commercial",
    "no_derivatives",
    "custom",
    "unclear",
    "missing",
]


# Reads configs/licenses.yaml and checks that every category in it is one we know.
# Inputs: path — the YAML file (defaults to configs/licenses.yaml).
# Returns: dict like {"mit": {"name": "MIT License", "category": "permissive"}, ...}
def load_license_table(path=LICENSES_FILE):
    with open(path, encoding="utf-8") as file:
        table = yaml.safe_load(file)["licenses"]
    for license_id, info in table.items():
        # A typo like "permisive" would silently break scoring later, so catch it now.
        if info.get("category") not in CATEGORY_ORDER:
            raise ValueError(f"Bad category for {license_id!r} in {path}: {info.get('category')!r}")
    return table


# Makes a license ID tidy: lowercase, no spaces around it. "  MIT " -> "mit".
# Inputs: license_id — raw text (may be None).
# Returns: cleaned text, or None if nothing is left.
def clean_license_id(license_id):
    if license_id is None:
        return None
    cleaned = str(license_id).strip().lower()
    return cleaned or None


# Looks up the category of ONE license ID.
# Inputs: license_id — cleaned ID like "mit"; table — from load_license_table().
# Returns: category text. IDs we have never seen count as "unclear", not as an error,
#          because HF can add new licenses at any time.
def category_for(license_id, table):
    info = table.get(license_id)
    if info is None:
        return "unclear"
    return info["category"]


# Picks the most restrictive category from a list.
# Why the strictest? A dataset that lists two licenses might mean "choose either one"
# or "parts are under each". We cannot tell which, so we assume the cautious case.
# Inputs: categories — list of category texts.
# Returns: the single strictest category ("missing" if the list is empty).
def pick_strictest_category(categories):
    if not categories:
        return "missing"
    return max(categories, key=CATEGORY_ORDER.index)


# The main function: turns raw license info into a clean summary.
# Inputs: tag_licenses — list from the "license:..." tags (may be None or empty);
#         license_name — the card's free-text license name, used with "other" (may be None);
#         table — from load_license_table().
# Returns: dict with
#   license_ids          sorted list of cleaned IDs, e.g. ["cc-by-sa-3.0", "gfdl"]
#   license_category     one category for the whole dataset
#   license_detail       the custom license name for "other" licenses, else None
#   has_multiple_licenses True if more than one license is listed
def normalize_license(tag_licenses, license_name, table):
    # set() removes duplicates; sorted() gives a stable order for tests and output.
    cleaned = {clean_license_id(value) for value in (tag_licenses or [])}
    license_ids = sorted(value for value in cleaned if value)

    categories = [category_for(license_id, table) for license_id in license_ids]
    license_category = pick_strictest_category(categories)

    license_detail = None
    if "other" in license_ids and license_name:
        license_detail = str(license_name).strip() or None

    return {
        "license_ids": license_ids,
        "license_category": license_category,
        "license_detail": license_detail,
        "has_multiple_licenses": len(license_ids) > 1,
    }
