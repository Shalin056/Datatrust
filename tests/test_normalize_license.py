"""
test_normalize_license.py — checks that license tags become the right IDs and categories.

Imports / uses: datatrust/pipelines/normalize_license.py, configs/licenses.yaml
Used by: pytest
"""

import pytest

from datatrust.pipelines.normalize_license import (
    CATEGORY_ORDER,
    clean_license_id,
    load_license_table,
    normalize_license,
    pick_strictest_category,
)


# Loads the real licenses.yaml once and shares it with every test in this file.
@pytest.fixture(scope="module")
def table():
    return load_license_table()


def test_table_loads_and_has_common_licenses(table):
    assert table["mit"]["category"] == "permissive"
    assert table["cc-by-nc-4.0"]["category"] == "non_commercial"
    assert table["cc0-1.0"]["category"] == "public_domain"


def test_table_rejects_unknown_category(tmp_path):
    bad_file = tmp_path / "licenses.yaml"
    bad_file.write_text("licenses:\n  mit: {name: MIT, category: permisive}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_license_table(bad_file)


def test_clean_license_id():
    assert clean_license_id("  MIT ") == "mit"
    assert clean_license_id("") is None
    assert clean_license_id(None) is None


def test_single_permissive_license(table):
    result = normalize_license(["mit"], None, table)
    assert result == {
        "license_ids": ["mit"],
        "license_category": "permissive",
        "license_detail": None,
        "has_multiple_licenses": False,
    }


def test_no_license_is_missing(table):
    assert normalize_license([], None, table)["license_category"] == "missing"
    assert normalize_license(None, None, table)["license_category"] == "missing"


def test_multiple_licenses_use_strictest(table):
    # Real example: Salesforce/wikitext lists both of these.
    result = normalize_license(["gfdl", "cc-by-sa-3.0"], None, table)
    assert result["license_ids"] == ["cc-by-sa-3.0", "gfdl"]
    assert result["license_category"] == "share_alike"
    assert result["has_multiple_licenses"] is True


def test_permissive_plus_non_commercial_is_non_commercial(table):
    result = normalize_license(["mit", "cc-by-nc-4.0"], None, table)
    assert result["license_category"] == "non_commercial"


def test_other_keeps_custom_name(table):
    result = normalize_license(["other"], " bedlam-non-commercial ", table)
    assert result["license_category"] == "custom"
    assert result["license_detail"] == "bedlam-non-commercial"


def test_license_name_ignored_when_not_other(table):
    # license_name only explains "other"; for a normal license it adds nothing.
    assert normalize_license(["mit"], "something", table)["license_detail"] is None


def test_unknown_and_unseen_ids_are_unclear(table):
    assert normalize_license(["unknown"], None, table)["license_category"] == "unclear"
    assert normalize_license(["brand-new-license"], None, table)["license_category"] == "unclear"


def test_duplicates_and_case_are_cleaned(table):
    result = normalize_license(["MIT", "mit", " mit "], None, table)
    assert result["license_ids"] == ["mit"]
    assert result["has_multiple_licenses"] is False


def test_strictest_follows_category_order():
    assert pick_strictest_category(["public_domain", "permissive"]) == "permissive"
    assert pick_strictest_category(["custom", "no_derivatives"]) == "custom"
    assert pick_strictest_category([]) == "missing"
    assert CATEGORY_ORDER[0] == "public_domain"
    assert CATEGORY_ORDER[-1] == "missing"
