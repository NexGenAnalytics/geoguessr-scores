from geoguessr_scraper.models import ScoreRow
from geoguessr_scraper.plots import (
    generate_all_plots,
    plot_average_scores,
    plot_score_distribution,
    plot_score_trends,
    plot_wins,
)
from geoguessr_scraper.stats import compute_player_stats


def row(date, player_id, name, score):
    return ScoreRow(
        challenge_date=date,
        challenge_token="tok",
        player_id=player_id,
        player_name=name,
        total_score=score,
        total_time_seconds=None,
        total_distance=None,
        scraped_at="t1",
    )


def make_rows():
    return [
        row("2026-07-13", "p1", "chad", 100),
        row("2026-07-14", "p1", "chad", 200),
        row("2026-07-13", "p2", "pat", 150),
        row("2026-07-14", "p2", "pat", 150),
    ]


def assert_is_png(path):
    assert path.is_file()
    assert path.stat().st_size > 0
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_all_plots_writes_four_pngs(tmp_path):
    rows = make_rows()
    stats = compute_player_stats(rows)
    written = generate_all_plots(rows, stats, tmp_path / "charts")
    assert len(written) == 4
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


def test_plots_handle_single_player_single_day(tmp_path):
    rows = [row("2026-07-14", "p1", "chad", 100)]
    stats = compute_player_stats(rows)
    written = generate_all_plots(rows, stats, tmp_path / "charts")
    for path in written:
        assert_is_png(path)
