from geoguessr_scraper.report_cli import main
from geoguessr_scraper.store import sync_rows
from geoguessr_scraper.models import ScoreRow


def make_row(date, player_id, name, score):
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


def test_missing_csv_reports_error(tmp_path, capsys):
    exit_code = main(["--csv", str(tmp_path / "nope.csv")])
    assert exit_code == 1
    assert "Run scrape.py first" in capsys.readouterr().err


def test_prints_table_and_writes_plots(tmp_path, capsys):
    csv_path = tmp_path / "scores.csv"
    sync_rows(csv_path, [make_row("2026-07-14", "p1", "chad", 21000), make_row("2026-07-14", "p2", "pat", 18000)])

    output_dir = tmp_path / "plots"
    exit_code = main(["--csv", str(csv_path), "--output-dir", str(output_dir)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "chad" in out
    assert "pat" in out
    assert "Saved 9 charts (weekdays only)" in out
    assert len(list(output_dir.glob("*.png"))) == 9


def test_weekend_games_are_left_out_of_charts_by_default(tmp_path, capsys):
    csv_path = tmp_path / "scores.csv"
    sync_rows(csv_path, [make_row("2026-07-18", "p1", "chad", 21000)])  # a Saturday

    output_dir = tmp_path / "plots"
    assert main(["--csv", str(csv_path), "--output-dir", str(output_dir)]) == 0
    assert "No weekday games to chart" in capsys.readouterr().out
    assert not output_dir.exists()

    assert main(["--csv", str(csv_path), "--output-dir", str(output_dir), "--include-weekends"]) == 0
    assert "Saved 9 charts (all days)" in capsys.readouterr().out


def test_no_plots_flag_skips_chart_generation(tmp_path, capsys):
    csv_path = tmp_path / "scores.csv"
    sync_rows(csv_path, [make_row("2026-07-14", "p1", "chad", 21000)])

    output_dir = tmp_path / "plots"
    exit_code = main(["--csv", str(csv_path), "--output-dir", str(output_dir), "--no-plots"])

    assert exit_code == 0
    assert "chad" in capsys.readouterr().out
    assert not output_dir.exists()
