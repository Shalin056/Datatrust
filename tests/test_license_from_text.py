"""
test_license_from_text.py — checks that licenses written in README text are found correctly.
Most examples are real License sections from our first collection (dataset name in comments).

Imports / uses: datatrust/pipelines/license_from_text.py, configs/license_aliases.yaml,
                configs/licenses.yaml
Used by: pytest
"""

import pytest

from datatrust.pipelines.license_from_text import (
    UNRECOGNISED_DETAIL,
    choose_license_source,
    find_license_ids,
    licenses_from_text,
    load_license_rules,
    normalize_text,
)


# Loads the real alias file once for all tests in this file.
@pytest.fixture(scope="module")
def rules():
    return load_license_rules()


# Shortcut: returns only the license IDs found in a text.
def ids_in(text, rules):
    return licenses_from_text(text, rules)["license_ids"]


def test_normalize_text():
    assert normalize_text("CC BY-NC-SA 4.0!") == "cc by nc sa 4 0"
    assert normalize_text(None) == ""


def test_unknown_license_id_in_aliases_fails_loudly(tmp_path):
    bad_file = tmp_path / "aliases.yaml"
    bad_file.write_text("aliases:\n  mitt: [mit]\nsignals: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_license_rules(bad_file)


def test_simple_names(rules):
    assert ids_in("MIT.", rules) == ["mit"]  # k9cli/video-vec2wav2-tokenizer
    assert ids_in("CC-BY-4.0", rules) == ["cc-by-4.0"]  # allenai/social_i_qa
    assert ids_in("This dataset is released under the **Apache-2.0 License**.", rules) == [
        "apache-2.0"
    ]  # IPEC-COMMUNITY/FastUMI_100k_lerobot


def test_long_names_and_urls(rules):
    # microsoft/NOTSOFAR
    text = (
        "The data is licensed under the Creative Commons Attribution 4.0 "
        "International License (CC BY 4.0)."
    )
    assert ids_in(text, rules) == ["cc-by-4.0"]
    # agibot-world/AgiBotWorld-Beta
    text = "All the data and code within this repo are under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)."
    assert ids_in(text, rules) == ["cc-by-nc-sa-4.0"]


def test_longer_license_is_not_also_counted_as_shorter(rules):
    # "cc by nc 4 0" must not also produce "cc-by-4.0".
    assert ids_in("Licensed under CC BY-NC 4.0.", rules) == ["cc-by-nc-4.0"]


def test_whole_words_only(rules):
    # "permit" contains "mit" but is not the MIT license.
    assert find_license_ids(normalize_text("we permit research use"), rules["aliases"]) == []


def test_code_sentences_are_ignored(rules):
    # ArneH/swiss-caselaw-web-ui: the code is MIT, the data is CC0.
    text = "Code: MIT. See [LICENSE](LICENSE). Dataset packaging and added metadata: CC0-1.0."
    assert ids_in(text, rules) == ["cc0-1.0"]


def test_mixed_licenses_need_a_human(rules):
    # hf-internal-testing/tokenizers-test-data
    text = "Corpora are small excerpts of public datasets, each under its own license."
    result = licenses_from_text(text, rules)
    assert result["license_ids"] == ["other"]
    assert result["detail"].startswith("mixed")


def test_restricted_text_needs_a_human(rules):
    result = licenses_from_text("Copyright © COGNOSPHERE. All Rights Reserved.", rules)
    assert result["license_ids"] == ["other"]  # simon3000/genshin-voice
    assert result["detail"].startswith("restricted")


def test_modified_mit_is_not_plain_mit(rules):
    # elefantai/p2p-full-data
    result = licenses_from_text("Released under a **Modified MIT License**.", rules)
    assert result["license_ids"] == ["mit", "other"]
    assert result["detail"].startswith("custom")


def test_own_community_license_needs_a_human(rules):
    # Skywork/SkyPile-150B
    text = "The community usage of SkyPile dataset requires Skywork Community License."
    assert licenses_from_text(text, rules)["detail"].startswith("custom")


def test_partly_new_partly_original_is_mixed(rules):
    # HuggingFaceTB/smoltalk: only the NEW parts are Apache 2.0.
    text = (
        "All the new datasets are licensed under Apache 2.0. For the existing public "
        "datasets, please refer to the original dataset for the license."
    )
    result = licenses_from_text(text, rules)
    assert result["license_ids"] == ["apache-2.0", "other"]
    assert result["detail"].startswith("mixed")


def test_many_licenses_listed_is_mixed(rules):
    # BAAI/CCI4.0-M2-Base-v1 lists one license per source dataset.
    text = "Sources: A (MIT), B (Apache 2.0), C (CC BY 4.0), D (ODC-By)."
    result = licenses_from_text(text, rules)
    assert "other" in result["license_ids"]
    assert result["detail"].startswith("mixed")


def test_html_comments_are_ignored(rules):
    # imageomics/fish-vista: the template's hidden notes list example licenses.
    text = "<!-- If you choose CC0: ... If you choose CC BY 4.0: ... --> NVIDIA License"
    assert ids_in(text, rules) == ["other"]


def test_not_specified_means_no_license(rules):
    # adityx23/icl-dataset
    text = "**Not specified.** No licence has been chosen for this data."
    assert licenses_from_text(text, rules) == {"license_ids": [], "detail": None}


def test_unrecognised_license_text_needs_a_human(rules):
    result = licenses_from_text("NVIDIA License", rules)  # nvidia/PointWorld-DROID
    assert result == {"license_ids": ["other"], "detail": UNRECOGNISED_DETAIL}


def test_empty_section(rules):
    assert licenses_from_text(None, rules) == {"license_ids": [], "detail": None}
    assert licenses_from_text("   ", rules) == {"license_ids": [], "detail": None}


def test_tags_win_over_card_text():
    text_result = {"license_ids": ["mit"], "detail": None}
    assert choose_license_source(["apache-2.0"], text_result) == (["apache-2.0"], "tag", None)


def test_card_text_used_when_no_tags():
    text_result = {"license_ids": ["other"], "detail": "mixed: x"}
    assert choose_license_source([], text_result) == (["other"], "card_text", "mixed: x")


def test_no_license_anywhere():
    text_result = {"license_ids": [], "detail": None}
    assert choose_license_source(None, text_result) == ([], "none", None)
