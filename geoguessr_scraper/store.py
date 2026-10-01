"""Read and write the scores CSV with upsert-by-key semantics.

Rows are keyed by (challenge_date, player_id), so re-running the scraper, or
merging runs from different coworkers, never produces duplicates.
"""

import csv
from dataclasses import replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .models import ScoreRow

COLUMNS = [
    "challenge_date",
    "challenge_token",
    "player_id",
    "player_name",
    "total_score",
    "total_time_seconds",
    "total_distance",
    "scraped_at",
    "round_scores",
]
DETAIL_FIELDS = ("challenge_token", "total_time_seconds", "total_distance", "round_scores")
ROUND_SEPARATOR = ";"


def format_round_scores(scores: Optional[Tuple[int, ...]]) -> str:
    return ROUND_SEPARATOR.join(str(s) for s in scores) if scores else ""


def parse_round_scores(value: Optional[str]) -> Optional[Tuple[int, ...]]:
    if not value:
        return None
    return tuple(int(s) for s in value.split(ROUND_SEPARATOR))


def _row_from_record(record: Dict[str, str]) -> ScoreRow:
    def opt_int(value: str):
        return int(float(value)) if value not in ("", None) else None

    def opt_float(value: str):
        return float(value) if value not in ("", None) else None

    return ScoreRow(
        challenge_date=record["challenge_date"],
        challenge_token=record.get("challenge_token", ""),
        player_id=record["player_id"],
        player_name=record.get("player_name", ""),
        total_score=int(float(record["total_score"])),
        total_time_seconds=opt_int(record.get("total_time_seconds", "")),
        total_distance=opt_float(record.get("total_distance", "")),
        scraped_at=record.get("scraped_at", ""),
        round_scores=parse_round_scores(record.get("round_scores")),
    )


def load_rows(path: Path) -> Dict[Tuple[str, str], ScoreRow]:
    """Load existing CSV rows keyed by (challenge_date, player_id)."""
    rows: Dict[Tuple[str, str], ScoreRow] = {}
    if not path.is_file():
        return rows
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            try:
                row = _row_from_record(record)
            except (KeyError, ValueError):
                continue  # skip malformed lines instead of losing the whole file
            rows[row.key] = row
    return rows


def _with_known_details(new: ScoreRow, current: ScoreRow) -> ScoreRow:
    """Keep details the old row had but the new scrape couldn't see (e.g. round scores)."""
    if new.total_score != current.total_score:
        return new
    kept = {f: getattr(current, f) for f in DETAIL_FIELDS if not getattr(new, f) and getattr(current, f)}
    return replace(new, **kept) if kept else new


def _comparable(row: ScoreRow) -> tuple:
    return (row.total_score, row.player_name) + tuple(getattr(row, f) for f in DETAIL_FIELDS)


def upsert_rows(
    existing: Dict[Tuple[str, str], ScoreRow], new_rows: Iterable[ScoreRow]
) -> Tuple[int, int]:
    """Merge new rows in place. Returns (added_count, updated_count)."""
    added = updated = 0
    for row in new_rows:
        current = existing.get(row.key)
        if current is None:
            added += 1
        else:
            row = _with_known_details(row, current)
            if _comparable(current) == _comparable(row):
                continue  # unchanged; keep original scraped_at
            updated += 1
        existing[row.key] = row
    return added, updated


def write_rows(path: Path, rows: Dict[Tuple[str, str], ScoreRow]) -> None:
    """Write all rows sorted by date (newest first) then score (highest first)."""
    ordered = sorted(
        rows.values(), key=lambda r: (r.challenge_date, r.total_score), reverse=True
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for row in ordered:
            record = {column: getattr(row, column) for column in COLUMNS}
            record["round_scores"] = format_round_scores(row.round_scores)
            writer.writerow([record[column] for column in COLUMNS])


def sync_rows(path: Path, new_rows: List[ScoreRow]) -> Tuple[int, int, int]:
    """Load, upsert, and save. Returns (added, updated, total)."""
    rows = load_rows(path)
    added, updated = upsert_rows(rows, new_rows)
    if added or updated or not path.is_file():
        write_rows(path, rows)
    return added, updated, len(rows)
