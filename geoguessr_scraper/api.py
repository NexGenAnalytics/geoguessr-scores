"""Thin HTTP client for the GeoGuessr web API."""

import time
from typing import Optional

import requests

BASE_URL = "https://www.geoguessr.com/api/v3"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 2.0
REQUEST_TIMEOUT = 20


class AuthError(Exception):
    """The _ncfa cookie is missing, expired, or invalid."""


class ApiError(Exception):
    """GeoGuessr returned an unexpected response."""


class GeoGuessrClient:
    def __init__(self, ncfa_cookie: str, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.cookies.set("_ncfa", ncfa_cookie, domain="www.geoguessr.com")
        self.session.headers["User-Agent"] = "geoguessr-daily-scraper/1.0"

    def _get(self, path: str) -> object:
        url = f"{BASE_URL}/{path}"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                if attempt == MAX_ATTEMPTS:
                    raise ApiError(f"Network error fetching {url}: {exc}") from exc
                time.sleep(BACKOFF_SECONDS * attempt)
                continue

            if response.status_code in (401, 403):
                raise AuthError(
                    "GeoGuessr rejected the session cookie (HTTP "
                    f"{response.status_code}). Log in at geoguessr.com and copy "
                    "a fresh _ncfa cookie into your .env file."
                )
            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS * attempt)
                continue
            if not response.ok:
                raise ApiError(f"HTTP {response.status_code} from {url}")

            try:
                return response.json()
            except ValueError as exc:
                raise ApiError(f"Non-JSON response from {url}") from exc
        raise ApiError(f"Giving up on {url} after {MAX_ATTEMPTS} attempts")

    def get_my_profile(self) -> dict:
        """The logged-in account's own profile, used to key rows by a stable id."""
        return self._get("profiles/")

    def get_month_summary(self, year: int, month: int) -> object:
        """The logged-in account's Daily Challenge results for one calendar month.

        Unlike the today/previous endpoints, this is not limited to a rolling
        few-day window; it's the same call GeoGuessr's own site uses to render
        the /daily-challenges/{date} history pages.
        """
        return self._get(f"challenges/daily-challenges/me/month?year={year}&month={month}")
