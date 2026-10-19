"""
test_hf_client.py — checks that the HF client retries, waits, and pages correctly.

Imports / uses: datatrust/collector/hf_client.py, tests/conftest.py (FakeResponse, FakeSession)
Used by: pytest
"""

import pytest
import requests

from datatrust.collector.hf_client import (
    HFClient,
    HFClientError,
    backoff_seconds,
    wait_seconds_for,
)
from tests.conftest import FakeResponse, FakeSession


def test_token_is_sent_in_header():
    session = FakeSession([])
    HFClient(token="hf_test", session=session)
    assert session.headers["Authorization"] == "Bearer hf_test"


def test_no_token_means_no_auth_header():
    session = FakeSession([])
    HFClient(token=None, session=session)
    assert "Authorization" not in session.headers


def test_success_on_first_try(no_sleep):
    session = FakeSession([FakeResponse(200)])
    response = HFClient(session=session).get("https://x")
    assert response.status_code == 200
    assert len(session.calls) == 1
    assert no_sleep == []


def test_retries_after_server_error(no_sleep):
    session = FakeSession([FakeResponse(503), FakeResponse(200)])
    response = HFClient(session=session).get("https://x")
    assert response.status_code == 200
    assert len(session.calls) == 2
    assert no_sleep == [2]  # first backoff wait


def test_rate_limit_waits_for_reset_time(no_sleep):
    limited = FakeResponse(429, headers={"RateLimit": '"api";r=0;t=40'})
    session = FakeSession([limited, FakeResponse(200)])
    HFClient(session=session).get("https://x")
    assert no_sleep == [41]


def test_retries_after_network_error(no_sleep):
    session = FakeSession([requests.ConnectionError("down"), FakeResponse(200)])
    response = HFClient(session=session).get("https://x")
    assert response.status_code == 200


def test_404_is_returned_without_retry(no_sleep):
    session = FakeSession([FakeResponse(404)])
    response = HFClient(session=session).get("https://x")
    assert response.status_code == 404
    assert len(session.calls) == 1


def test_gives_up_after_max_retries(no_sleep):
    session = FakeSession([FakeResponse(500)] * 3)
    with pytest.raises(HFClientError):
        HFClient(max_retries=3, session=session).get("https://x")
    assert len(session.calls) == 3
    assert len(no_sleep) == 2  # no wait after the final attempt


def test_backoff_grows_and_is_capped():
    assert backoff_seconds(1) == 2
    assert backoff_seconds(3) == 8
    assert backoff_seconds(20) == 60


def test_wait_uses_retry_after_when_no_ratelimit_header():
    response = FakeResponse(429, headers={"Retry-After": "7"})
    assert wait_seconds_for(response, attempt=1) == 7


def test_server_error_ignores_ratelimit_header():
    # A 500 is not a rate limit, so we use normal backoff, not the reset time.
    response = FakeResponse(500, headers={"RateLimit": '"api";r=10;t=200'})
    assert wait_seconds_for(response, attempt=1) == 2


def test_paged_json_follows_next_links():
    session = FakeSession([
        FakeResponse(200, json_data=[{"id": "a"}, {"id": "b"}], next_url="https://x?page=2"),
        FakeResponse(200, json_data=[{"id": "c"}]),
    ])
    items = list(HFClient(session=session).get_paged_json("https://x", params={"limit": 2}))
    assert [item["id"] for item in items] == ["a", "b", "c"]
    assert session.calls[1] == {"url": "https://x?page=2", "params": None}


def test_paged_json_raises_on_bad_status():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(HFClientError):
        list(HFClient(session=session).get_paged_json("https://x"))


def test_get_text_returns_none_for_missing_file():
    session = FakeSession([FakeResponse(404)])
    assert HFClient(session=session).get_text("https://x") == (404, None)
