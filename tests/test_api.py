import pytest

from geoguessr_scraper import api
from geoguessr_scraper.api import ApiError, AuthError, GeoGuessrClient


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Returns queued responses and records the URLs requested."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requested = []
        self.headers = {}
        self.cookies = self

    def set(self, *args, **kwargs):  # stands in for session.cookies.set
        self.cookie_args = (args, kwargs)

    def get(self, url, timeout=None):
        self.requested.append(url)
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda _: None)


def make_client(responses):
    session = FakeSession(responses)
    return GeoGuessrClient("cookie-value", session=session), session


def test_sets_ncfa_cookie():
    _, session = make_client([])
    args, kwargs = session.cookie_args
    assert args[0] == "_ncfa"
    assert args[1] == "cookie-value"


def test_expired_cookie_raises_auth_error():
    client, _ = make_client([FakeResponse(401)])
    with pytest.raises(AuthError, match="_ncfa"):
        client.get_my_profile()


def test_retries_server_errors_then_succeeds():
    client, session = make_client(
        [FakeResponse(503), FakeResponse(503), FakeResponse(200, {"user": {"id": "x"}})]
    )
    assert client.get_my_profile() == {"user": {"id": "x"}}
    assert len(session.requested) == 3


def test_gives_up_after_max_attempts():
    client, _ = make_client([FakeResponse(503)] * api.MAX_ATTEMPTS)
    with pytest.raises(ApiError):
        client.get_my_profile()


def test_unexpected_status_raises_api_error():
    client, _ = make_client([FakeResponse(404)])
    with pytest.raises(ApiError, match="404"):
        client.get_my_profile()


def test_profile_url():
    client, session = make_client([FakeResponse(200, {"user": {}})])
    client.get_my_profile()
    assert session.requested[0].endswith("/profiles/")


def test_month_summary_url():
    client, session = make_client([FakeResponse(200, [])])
    client.get_month_summary(2026, 7)
    assert session.requested[0].endswith("challenges/daily-challenges/me/month?year=2026&month=7")
