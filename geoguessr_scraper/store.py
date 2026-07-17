"""Read and write the scores CSV with upsert-by-key semantics.

Rows are keyed by (challenge_date, player_id), so re-running the scraper, or
merging runs from different coworkers, never produces duplicates.
"""

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

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
]


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


def upsert_rows(
    existing: Dict[Tuple[str, str], ScoreRow], new_rows: Iterable[ScoreRow]
) -> Tuple[int, int]:
    """Merge new rows in place. Returns (added_count, updated_count)."""
    added = updated = 0
    for row in new_rows:
        current = existing.get(row.key)
        if current is None:
            added += 1
        elif (current.total_score, current.player_name) != (row.total_score, row.player_name):
            updated += 1
        else:
            continue  # unchanged; keep original scraped_at
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
            writer.writerow([getattr(row, column) for column in COLUMNS])


def sync_rows(path: Path, new_rows: List[ScoreRow]) -> Tuple[int, int, int]:
    """Load, upsert, and save. Returns (added, updated, total)."""
    rows = load_rows(path)
    added, updated = upsert_rows(rows, new_rows)
    if added or updated or not path.is_file():
        write_rows(path, rows)
    return added, updated, len(rows)
