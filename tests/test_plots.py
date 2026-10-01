from geoguessr_scraper.models import ScoreRow
from geoguessr_scraper.plots import (
    generate_all_plots,
    plot_average_scores,
    plot_day_of_week,
    plot_five_ks,
    plot_head_to_head,
    plot_rolling_average,
    plot_round_averages,
    plot_score_distribution,
    plot_score_trends,
    plot_wins,
)
from geoguessr_scraper.stats import compute_player_stats


def row(date, player_id, name, score, rounds=None):
    return ScoreRow(
        challenge_date=date,
        challenge_token="tok",
        player_id=player_id,
        player_name=name,
        total_score=score,
        total_time_seconds=None,
        total_distance=None,
        scraped_at="t1",
        round_scores=rounds,
    )


def make_rows():
    return [
        row("2026-07-13", "p1", "chad", 100),
        row("2026-07-14", "p1", "chad", 200, rounds=(5000, 4000, 3000, 2000, 1000)),
        row("2026-07-13", "p2", "pat", 150, rounds=(5000, 5000, 5000, 5000, 5000)),
        row("2026-07-14", "p2", "pat", 150),
    ]


def assert_is_png(path):
    assert path.is_file()
    assert path.stat().st_size > 0
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_all_plots_writes_nine_pngs(tmp_path):
    rows = make_rows()
    stats = compute_player_stats(rows)
    written = generate_all_plots(rows, stats, tmp_path / "charts")
    assert len(written) == 9
    for path in written:
        assert_is_png(path)


def test_individual_plot_functions_write_valid_pngs(tmp_path):
    rows = make_rows()
    stats = compute_player_stats(rows)

    trend_path = tmp_path / "trend.png"
    plot_score_trends(rows, stats, trend_path)
    assert_is_png(trend_path)

    dist_path = tmp_path / "dist.png"
    plot_score_distribution(rows, stats, dist_path)
    assert_is_png(dist_path)

    avg_path = tmp_path / "avg.png"
    plot_average_scores(stats, avg_path)
    assert_is_png(avg_path)

    wins_path = tmp_path / "wins.png"
    plot_wins(stats, wins_path)
    assert_is_png(wins_path)

    for name, plot_fn in [
        ("rolling.png", plot_rolling_average),
        ("weekday.png", plot_day_of_week),
        ("h2h.png", plot_head_to_head),
        ("rounds.png", plot_round_averages),
    ]:
        plot_fn(rows, stats, tmp_path / name)
        assert_is_png(tmp_path / name)

    five_ks_path = tmp_path / "five_ks.png"
    plot_five_ks(stats, five_ks_path)
    assert_is_png(five_ks_path)


def test_round_plots_handle_no_round_data(tmp_path):
    rows = [row("2026-07-14", "p1", "chad", 100), row("2026-07-14", "p2", "pat", 90)]
    stats = compute_player_stats(rows)
    plot_five_ks(stats, tmp_path / "five_ks.png")
    plot_round_averages(rows, stats, tmp_path / "rounds.png")
    assert_is_png(tmp_path / "five_ks.png")
    assert_is_png(tmp_path / "rounds.png")


def test_plots_handle_single_player_single_day(tmp_path):
    rows = [row("2026-07-14", "p1", "chad", 100)]
    stats = compute_player_stats(rows)
    written = generate_all_plots(rows, stats, tmp_path / "charts")
    for path in written:
        assert_is_png(path)
