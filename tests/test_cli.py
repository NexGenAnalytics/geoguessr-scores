import argparse
from datetime import datetime as real_datetime
from datetime import timezone

import pytest

from geoguessr_scraper import cli
from geoguessr_scraper.cli import build_parser, main, months_between, scrape, valid_date


class FakeClient:
    """Serves a canned profile and canned month summaries without any network."""

    def __init__(self, profile, summaries_by_month, daily_challenges=(), games_by_token=None):
        self._profile = profile
        self._summaries = summaries_by_month
        self._daily = list(daily_challenges)
        self._games = games_by_token or {}
        self.requested_months = []
        self.requested_tokens = []

    def get_my_profile(self):
        return self._profile

    def get_month_summary(self, year, month):
        self.requested_months.append((year, month))
        return self._summaries.get((year, month), [])

    def get_today_daily_challenge(self):
        return self._daily[0] if self._daily else {}

    def get_previous_daily_challenges(self):
        return self._daily[1:]

    def get_my_challenge_game(self, token):
        self.requested_tokens.append(token)
        game = self._games.get(token)
        if isinstance(game, Exception):
            raise game
        return game or {}


class FrozenDatetime(real_datetime):
    """Pins "now" so default date-range tests don't depend on the real clock."""

    _frozen = real_datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls._frozen


@pytest.fixture(autouse=True)
def no_delay_and_frozen_clock(monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    monkeypatch.setattr(cli, "datetime", FrozenDatetime)


def make_client():
    profile = {"user": {"id": "p1", "nick": "chad"}}
    summaries = {
        (2026, 7): [
            {"day": 16, "totalScore": 21000},
            {"day": 15, "totalScore": 18000},
            {"day": 14, "totalScore": None, "wasFrozen": False},  # not played
        ],
        (2026, 6): [
            {"day": 30, "totalScore": 9000},
        ],
    }
    return FakeClient(profile, summaries)


def test_valid_date_accepts_iso_and_rejects_garbage():
    assert valid_date("2026-07-16") == "2026-07-16"
    for bad in ("7/16/2026", "2026-13-01", "yesterday"):
        with pytest.raises(argparse.ArgumentTypeError):
            valid_date(bad)


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.from_date is None
    assert args.to_date is None
    assert str(args.csv) == "scores.csv"


def test_months_between_same_month():
    assert months_between(real_datetime(2026, 7, 3).date(), real_datetime(2026, 7, 20).date()) == [
        (2026, 7)
    ]


def test_months_between_spans_year_boundary():
    assert months_between(real_datetime(2025, 12, 15).date(), real_datetime(2026, 1, 5).date()) == [
        (2025, 12),
        (2026, 1),
    ]


def test_scrape_default_range_uses_frozen_today():
    client = make_client()
    rows = scrape(client)  # default: 100 days before 2026-07-16 (2026-04-07) through 2026-07-16
    assert client.requested_months == [(2026, 4), (2026, 5), (2026, 6), (2026, 7)]
    assert [(r.challenge_date, r.total_score) for r in rows] == [
        ("2026-06-30", 9000),
        ("2026-07-15", 18000),
        ("2026-07-16", 21000),
    ]


def test_scrape_explicit_range_spans_previous_month():
    client = make_client()
    rows = scrape(client, from_date="2026-06-25", to_date="2026-07-15")
    assert client.requested_months == [(2026, 6), (2026, 7)]
    assert [(r.challenge_date, r.total_score) for r in rows] == [
        ("2026-06-30", 9000),
        ("2026-07-15", 18000),
    ]


def test_scrape_skips_unplayed_days():
    client = make_client()
    rows = scrape(client, from_date="2026-07-14", to_date="2026-07-14")
    assert rows == []


def finished_game(round_points, total_time=600):
    guesses = [{"roundScoreInPoints": points} for points in round_points]
    return {"state": "finished", "player": {"id": "p1", "totalTime": total_time, "guesses": guesses}}


def test_scrape_adds_round_details_from_own_game():
    """Regression: round scores used to come from the friends leaderboard, which
    leaves out some players entirely, so their rows never got round scores."""
    client = make_client()
    client._daily = [
        {"date": "2026-07-16T17:00:00Z", "token": "today"},
        {"date": "2026-07-15T17:00:00Z", "token": "yesterday"},
    ]
    client._games = {"today": finished_game((5000, 4000, 4000, 4000, 4000)), "yesterday": finished_game((1,) * 5)}
    rows = {r.challenge_date: r for r in scrape(client)}

    assert client.requested_tokens == ["yesterday", "today"]
    assert rows["2026-07-16"].round_scores == (5000, 4000, 4000, 4000, 4000)
    assert rows["2026-07-16"].challenge_token == "today"
    assert rows["2026-07-16"].total_time_seconds == 600
    assert rows["2026-07-15"].round_scores == (1,) * 5


def test_scrape_keeps_going_when_a_game_fails_to_load(capsys):
    client = make_client()
    client._daily = [
        {"date": "2026-07-16T17:00:00Z", "token": "today"},
        {"date": "2026-07-15T17:00:00Z", "token": "yesterday"},
    ]
    client._games = {"today": finished_game((5000,) * 5), "yesterday": cli.ApiError("HTTP 404")}
    rows = {r.challenge_date: r for r in scrape(client)}

    assert rows["2026-07-16"].round_scores == (5000,) * 5
    assert rows["2026-07-15"].round_scores is None
    assert "couldn't load your 2026-07-15 game (HTTP 404)" in capsys.readouterr().out


def test_scrape_raises_when_profile_has_no_id():
    client = FakeClient({"user": {}}, {})
    with pytest.raises(cli.ApiError, match="account id"):
        scrape(client)


def test_scrape_warns_on_unparseable_month(capsys):
    client = FakeClient(
        {"user": {"id": "p1", "nick": "chad"}},
        {(2026, 7): [{"unexpectedField": "??"}]},
    )
    rows = scrape(client, from_date="2026-07-01", to_date="2026-07-16")
    assert rows == []
    assert "unexpected fields" in capsys.readouterr().out


def test_main_rejects_inverted_range(capsys):
    assert main(["--from", "2026-07-16", "--to", "2026-07-10"]) == 1
    assert "--from must be on or before --to" in capsys.readouterr().err


def test_main_rejects_malformed_date():
    with pytest.raises(SystemExit):
        main(["--from", "not-a-date"])
