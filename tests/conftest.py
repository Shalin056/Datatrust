"""
conftest.py — shared test helpers. pytest loads this file automatically before tests run.
Here we build a FAKE internet connection, so tests never call the real Hugging Face API
(tests stay fast, free, and give the same result every time).

Imports / uses: pytest
Used by: tests/test_hf_client.py, tests/test_fetch_datasets.py, tests/test_fetch_cards.py
"""

import pytest


class FakeResponse:
    # Pretends to be a requests.Response with just the parts our code reads.
    # Inputs: status_code — e.g. 200; json_data — what .json() returns; text — body text;
    #         headers — dict of headers; next_url — address of the next page, if any.
    # Returns: nothing (builds the object).
    def __init__(self, status_code=200, json_data=None, text="", headers=None, next_url=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}
        self.encoding = None
        self.links = {"next": {"url": next_url}} if next_url else {}

    # Returns the fake JSON body.
    def json(self):
        return self._json_data


class FakeSession:
    # Pretends to be a requests.Session. It hands back prepared answers in order
    # and remembers every URL it was asked for, so tests can check them.
    # Inputs: responses — list of FakeResponse objects, or exceptions to raise.
    # Returns: nothing (builds the object).
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    # Records the call and returns (or raises) the next prepared answer.
    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        answer = self.responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


# Replaces time.sleep with a fake, so retry tests finish instantly.
# The waits that would have happened are stored in a list the test can inspect.
@pytest.fixture
def no_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr("datatrust.collector.hf_client.time.sleep", waits.append)
    return waits
