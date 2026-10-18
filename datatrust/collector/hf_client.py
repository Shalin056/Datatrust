"""
hf_client.py — a small, careful wrapper around the Hugging Face HTTP API.
It adds your token, retries when the server is busy, and waits politely when we hit
the rate limit (the maximum number of requests HF allows in 5 minutes).

Imports / uses: requests, datatrust/logging_setup.py
Used by: datatrust/collector/fetch_datasets.py, datatrust/collector/fetch_cards.py,
         datatrust/collector/run_collect.py
"""

import re
import time

import requests

from datatrust.logging_setup import get_logger

logger = get_logger("hf_client")

# Status codes that mean "try again later": 429 = too many requests, 5xx = server trouble.
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
USER_AGENT = "datatrust/0.1 (+https://github.com/Shalin056/Datatrust)"
MAX_BACKOFF_SECONDS = 60


# Raised when a request still fails after all retries, so callers can decide what to do.
class HFClientError(Exception):
    pass


class HFClient:
    # Sets up the client.
    # Inputs: token — HF token or None; timeout — seconds per request;
    #         max_retries — total attempts per request; session — optional requests.Session
    #         (tests pass a fake one here so no real network calls are made).
    # Returns: nothing (it builds the client object).
    def __init__(self, token=None, timeout=30, max_retries=5, session=None):
        self.timeout = timeout
        self.max_retries = max_retries
        # A Session reuses the same connection for many requests, which is faster.
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    # Sends one GET request, retrying on busy/server errors and network problems.
    # Inputs: url — address to call; params — optional dict of query settings.
    # Returns: the final requests.Response. Errors like 404 are returned, NOT retried,
    #          because asking again will not change the answer.
    def get(self, url, params=None):
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as error:
                # Network hiccup (Wi-Fi drop, slow server): wait, then try again.
                wait = backoff_seconds(attempt)
                logger.warning(f"Network error ({error.__class__.__name__}), retry in {wait}s")
                self._wait_before_retry(attempt, wait, url)
                continue

            if response.status_code not in RETRY_STATUS_CODES:
                return response

            wait = wait_seconds_for(response, attempt)
            logger.warning(f"HTTP {response.status_code} for {url}, retry in {wait}s")
            self._wait_before_retry(attempt, wait, url)

        raise HFClientError(f"Gave up after {self.max_retries} attempts: {url}")

    # Calls a paged API endpoint and yields every item from every page.
    # HF puts the address of the next page in the "Link" header; we follow it until
    # there is no next page.
    # Inputs: url — first page address; params — query settings for the first page.
    # Yields: one item (dict) at a time.
    def get_paged_json(self, url, params=None):
        next_url = url
        next_params = params
        while next_url:
            response = self.get(next_url, params=next_params)
            if response.status_code != 200:
                raise HFClientError(f"HTTP {response.status_code} for {next_url}")
            for item in response.json():
                yield item
            # The "next" link already contains all settings, so we stop sending params.
            next_url = response.links.get("next", {}).get("url")
            next_params = None

    # Downloads a text file (like a README).
    # Inputs: url — address of the file.
    # Returns: (status_code, text). text is None when the status is not 200.
    def get_text(self, url):
        response = self.get(url)
        if response.status_code != 200:
            return response.status_code, None
        # HF serves READMEs as UTF-8; setting it avoids garbled characters.
        response.encoding = "utf-8"
        return response.status_code, response.text

    # Sleeps before the next attempt, except after the last attempt (no point waiting).
    # Inputs: attempt — which try this was; wait — seconds; url — for the log message.
    # Returns: nothing.
    def _wait_before_retry(self, attempt, wait, url):
        if attempt < self.max_retries:
            time.sleep(wait)
        else:
            logger.error(f"No retries left for {url}")


# How long to wait after a failed attempt, growing each time: 2, 4, 8, 16... up to 60 seconds.
# This is called "exponential backoff": it gives a struggling server more and more room.
# Inputs: attempt — 1 for the first try, 2 for the second, ...
# Returns: seconds to wait (int).
def backoff_seconds(attempt):
    return min(2**attempt, MAX_BACKOFF_SECONDS)


# Decides how long to wait after a "try again" response.
# For 429 (rate limited), HF tells us when the limit resets, so we wait exactly that long:
#   RateLimit: "api";r=0;t=213   ->  r = requests left, t = seconds until reset
# Inputs: response — the failed response; attempt — which try this was.
# Returns: seconds to wait (int).
def wait_seconds_for(response, attempt):
    if response.status_code == 429:
        match = re.search(r"t=(\d+)", response.headers.get("RateLimit", ""))
        if match:
            # +1 second so we don't arrive a moment too early.
            return int(match.group(1)) + 1
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return int(retry_after)
    return backoff_seconds(attempt)
