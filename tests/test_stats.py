from geoguessr_scraper.models import ScoreRow
from geoguessr_scraper.stats import (
    average_by_round,
    average_by_weekday,
    compute_daily_winners,
    compute_player_stats,
    group_by_player,
    head_to_head,
    latest_name_by_player,
    rolling_mean,
    weekday_rows,
)


def row(date, player_id, name, score, scraped="t1", rounds=None):
    return ScoreRow(
        challenge_date=date,
        challenge_token="tok",
        player_id=player_id,
        player_name=name,
        total_score=score,
        total_time_seconds=None,
        total_distance=None,
        scraped_at=scraped,
        round_scores=rounds,
    )


def test_group_by_player():
    rows = [row("2026-07-14", "p1", "chad", 100), row("2026-07-15", "p1", "chad", 200), row("2026-07-14", "p2", "pat", 150)]
    grouped = group_by_player(rows)
    assert set(grouped.keys()) == {"p1", "p2"}
    assert len(grouped["p1"]) == 2


def test_latest_name_by_player_uses_most_recent_scrape():
    rows = [
        row("2026-07-14", "p1", "chadwick", 100, scraped="2026-07-14T00:00:00"),
        row("2026-07-15", "p1", "chad", 200, scraped="2026-07-15T00:00:00"),
    ]
    assert latest_name_by_player(rows) == {"p1": "chad"}


def test_compute_daily_winners_single_winner():
    rows = [row("2026-07-14", "p1", "chad", 200), row("2026-07-14", "p2", "pat", 100)]
    assert compute_daily_winners(rows) == {"2026-07-14": {"p1"}}


def test_compute_daily_winners_ties_both_win():
    rows = [row("2026-07-14", "p1", "chad", 200), row("2026-07-14", "p2", "pat", 200)]
    assert compute_daily_winners(rows) == {"2026-07-14": {"p1", "p2"}}


def test_compute_player_stats_values():
    rows = [
        row("2026-07-13", "p1", "chad", 100),
        row("2026-07-14", "p1", "chad", 200),
        row("2026-07-13", "p2", "pat", 50),
        row("2026-07-14", "p2", "pat", 50),
    ]
    stats = compute_player_stats(rows)
    by_id = {s.player_id: s for s in stats}

    chad = by_id["p1"]
    assert chad.games_played == 2
    assert chad.average_score == 150
    assert chad.median_score == 150
    assert chad.best_score == 200
    assert chad.worst_score == 100
    assert chad.wins == 2  # beat pat on both 07-13 (100>50) and 07-14 (200>50)
    assert chad.win_rate == 1.0

    pat = by_id["p2"]
    assert pat.games_played == 2
    assert pat.average_score == 50
    assert pat.worst_score == 50
    assert pat.best_score == 50


def test_compute_player_stats_wins_and_ranking_precisely():
    rows = [
        row("2026-07-13", "p1", "chad", 100),  # chad wins 07-13
        row("2026-07-13", "p2", "pat", 50),
        row("2026-07-14", "p1", "chad", 200),  # chad wins 07-14
        row("2026-07-14", "p2", "pat", 200),  # tie: pat also wins 07-14
    ]
    stats = compute_player_stats(rows)
    by_id = {s.player_id: s for s in stats}
    assert by_id["p1"].wins == 2  # won both days
    assert by_id["p2"].wins == 1  # tied on the second day only
    # sorted by average_score descending
    assert stats[0].player_id == "p1"


def test_compute_player_stats_stdev_zero_for_single_game():
    rows = [row("2026-07-14", "p1", "chad", 100)]
    stats = compute_player_stats(rows)
    assert stats[0].score_stdev == 0.0
    assert stats[0].games_played == 1


def test_weekday_rows_drops_saturday_and_sunday():
    rows = [
        row("2026-07-13", "p1", "chad", 100),  # Monday
        row("2026-07-17", "p1", "chad", 100),  # Friday
        row("2026-07-18", "p1", "chad", 100),  # Saturday
        row("2026-07-19", "p1", "chad", 100),  # Sunday
    ]
    assert [r.challenge_date for r in weekday_rows(rows)] == ["2026-07-13", "2026-07-17"]


def test_compute_player_stats_counts_five_ks_only_from_tracked_rounds():
    rows = [
        row("2026-07-13", "p1", "chad", 20000, rounds=(5000, 4000, 5000, 3000, 3000)),
        row("2026-07-14", "p1", "chad", 21000),  # no round data for this day
        row("2026-07-13", "p2", "pat", 18000),
    ]
    by_id = {s.player_id: s for s in compute_player_stats(rows)}
    assert by_id["p1"].five_ks == 2
    assert by_id["p1"].rounds_tracked == 5
    assert by_id["p1"].five_k_rate == 0.4
    assert by_id["p2"].rounds_tracked == 0
    assert by_id["p2"].five_k_rate == 0.0


def test_average_by_weekday_groups_by_day_name():
    rows = [
        row("2026-07-13", "p1", "chad", 100),  # Monday
        row("2026-07-20", "p1", "chad", 300),  # next Monday
        row("2026-07-14", "p1", "chad", 50),  # Tuesday
    ]
    assert average_by_weekday(rows) == {"p1": {0: 200, 1: 50}}


def test_average_by_round_skips_days_without_round_data():
    rows = [
        row("2026-07-13", "p1", "chad", 0, rounds=(5000, 4000, 3000, 2000, 1000)),
        row("2026-07-14", "p1", "chad", 0, rounds=(3000, 4000, 5000, 2000, 1000)),
        row("2026-07-15", "p1", "chad", 0),
        row("2026-07-13", "p2", "pat", 0),
    ]
    assert average_by_round(rows) == {"p1": [4000, 4000, 4000, 2000, 1000]}


def test_rolling_mean_uses_partial_window_at_start():
    assert rolling_mean([10, 20, 30, 40], 2) == [10, 15, 25, 35]


def test_head_to_head_counts_strict_wins_on_shared_days():
    rows = [
        row("2026-07-13", "p1", "chad", 200),
        row("2026-07-13", "p2", "pat", 100),
        row("2026-07-14", "p1", "chad", 100),
        row("2026-07-14", "p2", "pat", 100),  # tie: nobody gets the win
        row("2026-07-15", "p1", "chad", 100),  # pat didn't play: not a shared day
    ]
    records = head_to_head(rows)
    assert records[("p1", "p2")] == (1, 2)
    assert records[("p2", "p1")] == (0, 2)
