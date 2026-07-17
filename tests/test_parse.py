from geoguessr_scraper.parse import (
    iter_month_entries,
    profile_identity,
    score_row_from_month_entry,
)

SCRAPED_AT = "2026-07-16T00:00:00+00:00"


def test_profile_identity_extracts_id_and_nick():
    payload = {"user": {"id": "abc123", "nick": "chad"}}
    assert profile_identity(payload) == ("abc123", "chad")


def test_profile_identity_falls_back_to_alternate_key_names():
    payload = {"user": {"userId": "abc123", "name": "chad"}}
    assert profile_identity(payload) == ("abc123", "chad")


def test_profile_identity_handles_missing_or_malformed():
    assert profile_identity({}) is None
    assert profile_identity({"user": "not-a-dict"}) is None
    assert profile_identity({"user": {"nick": "no-id"}}) is None


def test_iter_month_entries_accepts_bare_list():
    payload = [{"day": 1}, {"day": 2}]
    assert iter_month_entries(payload) == payload


def test_iter_month_entries_unwraps_known_keys():
    for key in ("results", "days", "entries", "items", "summary"):
        payload = {key: [{"day": 1}]}
        assert iter_month_entries(payload) == [{"day": 1}]


def test_iter_month_entries_handles_unknown_shape():
    assert iter_month_entries({"unexpected": []}) == []
    assert iter_month_entries(None) == []
    assert iter_month_entries("not json") == []


def test_score_row_from_month_entry_real_shape():
    """Actual /me/month response shape, verified 2026-07-16: day-of-month int,
    no date string, no token, no time/distance."""
    entry = {
        "day": 16,
        "dayOfWeek": 4,
        "totalScore": 23484,
        "medal": "Gold",
        "nextDailyBadge": None,
        "wasFrozen": False,
        "isPartOfCurrentStreak": True,
    }
    row = score_row_from_month_entry(entry, 2026, 7, "p1", "chad", SCRAPED_AT)
    assert row.challenge_date == "2026-07-16"
    assert row.total_score == 23484
    assert row.challenge_token == ""
    assert row.total_time_seconds is None
    assert row.total_distance is None
    assert row.player_id == "p1"
    assert row.player_name == "chad"


def test_score_row_from_month_entry_unplayed_or_frozen_day_returns_none():
    unplayed = {"day": 9, "dayOfWeek": 5, "totalScore": None, "medal": None, "wasFrozen": False}
    frozen = {"day": 4, "dayOfWeek": 6, "totalScore": None, "medal": None, "wasFrozen": True}
    assert score_row_from_month_entry(unplayed, 2026, 7, "p1", "chad", SCRAPED_AT) is None
    assert score_row_from_month_entry(frozen, 2026, 7, "p1", "chad", SCRAPED_AT) is None


def test_score_row_from_month_entry_prefers_full_date_string_if_present():
    entry = {"date": "2026-07-14T00:00:00Z", "totalScore": 18000}
    row = score_row_from_month_entry(entry, 2026, 6, "p1", "chad", SCRAPED_AT)
    assert row.challenge_date == "2026-07-14"  # not 2026-06, ignores the passed-in month


def test_score_row_from_month_entry_missing_day_and_date_returns_none():
    assert score_row_from_month_entry({"totalScore": 100}, 2026, 7, "p1", "chad", SCRAPED_AT) is None
