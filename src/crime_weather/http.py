"""Shared HTTP session with retries and exponential backoff."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "la-crime-weather/0.1 (student portfolio project; github.com/SaraArmengol)"


def make_session(total_retries: int = 5, backoff: float = 1.0) -> requests.Session:
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff,  # waits 1s, 2s, 4s, ...
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session
