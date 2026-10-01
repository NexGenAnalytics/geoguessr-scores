from dataclasses import replace

from geoguessr_scraper.models import ScoreRow
from geoguessr_scraper.store import load_rows, sync_rows, upsert_rows, write_rows


def make_row(date="2026-07-15", player_id="p1", name="chad", score=20000, scraped="t1", rounds=None):
    return ScoreRow(
        challenge_date=date,
        challenge_token="tok",
        player_id=player_id,
        player_name=name,
        total_score=score,
        total_time_seconds=300,
        total_distance=12.5,
        scraped_at=scraped,
        round_scores=rounds,
    )


def test_sync_creates_csv_and_roundtrips(tmp_path):
    path = tmp_path / "scores.csv"
    added, updated, total = sync_rows(path, [make_row()])
    assert (added, updated, total) == (1, 0, 1)

    loaded = list(load_rows(path).values())
    assert len(loaded) == 1
    assert loaded[0] == make_row()


def test_round_scores_roundtrip(tmp_path):
    path = tmp_path / "scores.csv"
    sync_rows(path, [make_row(rounds=(5000, 4000, 3000, 2000, 1000))])
    assert list(load_rows(path).values())[0].round_scores == (5000, 4000, 3000, 2000, 1000)


def test_round_scores_arriving_later_count_as_an_update():
    rows = {make_row().key: make_row()}
    added, updated = upsert_rows(rows, [make_row(rounds=(5000,) * 4 + (0,))])
    assert (added, updated) == (0, 1)


def test_rescrape_without_round_data_keeps_existing_details():
    original = make_row(rounds=(5000,) * 4 + (0,))
    rows = {original.key: original}
    month_only = replace(original, challenge_token="", total_time_seconds=None, total_distance=None, round_scores=None)
    added, updated = upsert_rows(rows, [replace(month_only, player_name="chadwick")])
    assert (added, updated) == (0, 1)
    assert rows[original.key].player_name == "chadwick"
    assert rows[original.key].round_scores == original.round_scores
    assert rows[original.key].total_time_seconds == 300


def test_rescrape_with_new_score_drops_stale_details():
    rows = {make_row().key: make_row(rounds=(5000,) * 4 + (0,))}
    upsert_rows(rows, [make_row(score=21000)])
    assert rows[make_row().key].round_scores is None


def test_rerun_is_idempotent(tmp_path):
    path = tmp_path / "scores.csv"
    sync_rows(path, [make_row()])
    added, updated, total = sync_rows(path, [make_row(scraped="t2")])
    assert (added, updated, total) == (0, 0, 1)
    # Unchanged rows keep their original scraped_at.
    assert list(load_rows(path).values())[0].scraped_at == "t1"


def test_upsert_updates_changed_score():
    rows = {make_row().key: make_row()}
    added, updated = upsert_rows(rows, [make_row(score=21000)])
    assert (added, updated) == (0, 1)
    assert rows[make_row().key].total_score == 21000


def test_merging_two_coworkers_runs(tmp_path):
    """Two people scraping different friend groups can share one CSV."""
    path = tmp_path / "scores.csv"
    sync_rows(path, [make_row(player_id="p1"), make_row(player_id="p2", name="pat")])
    added, updated, total = sync_rows(
        path, [make_row(player_id="p2", name="pat"), make_row(player_id="p3", name="sam")]
    )
    assert (added, updated, total) == (1, 0, 3)


def test_write_sorts_newest_date_then_highest_score(tmp_path):
    path = tmp_path / "scores.csv"
    rows = [
        make_row(date="2026-07-14", player_id="a", score=5000),
        make_row(date="2026-07-15", player_id="b", score=9000),
        make_row(date="2026-07-15", player_id="c", score=25000),
    ]
    write_rows(path, {r.key: r for r in rows})
    ordered = [(r.challenge_date, r.total_score) for r in load_rows(path).values()]
    assert ordered == [("2026-07-15", 25000), ("2026-07-15", 9000), ("2026-07-14", 5000)]


def test_load_skips_malformed_lines(tmp_path):
    path = tmp_path / "scores.csv"
    sync_rows(path, [make_row()])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("2026-07-15,tok,p9,broken,not-a-number,,,t1\n")
    assert len(load_rows(path)) == 1


def test_load_missing_file_returns_empty(tmp_path):
    assert load_rows(tmp_path / "nope.csv") == {}
