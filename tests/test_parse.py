from geoguessr_scraper.parse import (
    daily_tokens_by_date,
    iter_month_entries,
    player_result,
    profile_identity,
    round_scores_from_result,
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


def test_daily_tokens_by_date_skips_entries_missing_fields():
    challenges = [
        {"date": "2026-09-30T16:56:19.4283785Z", "token": "abc"},
        {"date": "2026-09-29T16:56:19Z", "token": None},
        "not a dict",
    ]
    assert daily_tokens_by_date(challenges) == {"2026-09-30": "abc"}


def make_result(player_id, round_points):
    guesses = [{"roundScoreInPoints": points, "roundScore": {"amount": str(points)}} for points in round_points]
    return {"game": {"player": {"id": player_id, "totalTime": 900, "guesses": guesses}}}


def test_player_result_finds_own_game_among_friends():
    payload = {"items": [make_result("friend", [1] * 5), make_result("me", [2] * 5)]}
    assert player_result(payload, "me")["guesses"][0]["roundScoreInPoints"] == 2
    assert player_result(payload, "stranger") is None
    assert player_result({"unexpected": []}, "me") is None


def test_round_scores_from_result_real_shape():
    player = make_result("me", [4845, 5000, 4757, 4466, 4050])["game"]["player"]
    assert round_scores_from_result(player) == (4845, 5000, 4757, 4466, 4050)


def test_round_scores_from_result_falls_back_to_round_score_amount():
    player = {"guesses": [{"roundScore": {"amount": "5000"}}, {"roundScore": {"amount": "12"}}]}
    assert round_scores_from_result(player) == (5000, 12)


def test_round_scores_from_result_handles_missing_guesses():
    assert round_scores_from_result({}) is None
    assert round_scores_from_result({"guesses": [{"nothing": 1}]}) is None
