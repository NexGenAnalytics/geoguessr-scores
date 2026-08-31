"""Command line entry point: scrape your own Daily Challenge scores into the CSV."""

import argparse
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from .api import ApiError, AuthError, GeoGuessrClient
from .config import ConfigError, load_ncfa_cookie
from .models import ScoreRow
from .parse import iter_month_entries, profile_identity, score_row_from_month_entry
from .store import sync_rows

REQUEST_DELAY_SECONDS = 1.0
DEFAULT_LOOKBACK_DAYS = 100  # matches what GeoGuessr's own "past week" widget shows


def valid_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid date (use YYYY-MM-DD)")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape your own GeoGuessr Daily Challenge scores into a CSV."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("scores.csv"),
        help="Path to the output CSV (default: scores.csv)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to the .env file holding GEOGUESSR_NCFA (default: .env)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=valid_date,
        default=None,
        metavar="YYYY-MM-DD",
        help=f"First day to scrape (default: {DEFAULT_LOOKBACK_DAYS} days before today)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=valid_date,
        default=None,
        metavar="YYYY-MM-DD",
        help="Last day to scrape (default: today)",
    )
    return parser


def months_between(start: date, end: date) -> List[Tuple[int, int]]:
    """Every (year, month) from start to end, inclusive."""
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            month, year = 1, year + 1
    return months


def scrape(
    client: GeoGuessrClient,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[ScoreRow]:
    """Fetch your own Daily Challenge scores for the requested date range."""
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = datetime.now(timezone.utc).date()
    start = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else today - timedelta(
        days=DEFAULT_LOOKBACK_DAYS
    )
    end = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else today

    profile = client.get_my_profile()
    identity = profile_identity(profile)
    if identity is None:
        raise ApiError(
            "Could not determine your GeoGuessr account id from the profile "
            "response; the API may have changed."
        )
    player_id, player_name = identity

    rows: List[ScoreRow] = []
    for year, month in months_between(start, end):
        payload = client.get_month_summary(year, month)
        entries = iter_month_entries(payload)
        month_rows = []
        for entry in entries:
            row = score_row_from_month_entry(entry, year, month, player_id, player_name, scraped_at)
            if row:
                month_rows.append(row)
        if entries and not month_rows:
            sample = sorted(entries[0].keys())
            print(
                f"  warning: {year}-{month:02d} returned {len(entries)} entries "
                f"but none could be parsed (unexpected fields: {sample})"
            )
        rows.extend(month_rows)
        time.sleep(REQUEST_DELAY_SECONDS)

    start_str, end_str = start.isoformat(), end.isoformat()
    in_range = sorted(
        (r for r in rows if start_str <= r.challenge_date <= end_str),
        key=lambda r: r.challenge_date,
    )
    for row in in_range:
        print(f"  {row.challenge_date}: {row.total_score} points")
    if not in_range:
        print(f"  no played days found between {start_str} and {end_str}")
    return in_range


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.from_date and args.to_date and args.from_date > args.to_date:
        print("Error: --from must be on or before --to", file=sys.stderr)
        return 1

    try:
        cookie = load_ncfa_cookie(args.env_file)
        client = GeoGuessrClient(cookie)
        print("Fetching daily challenges...")
        rows = scrape(client, args.from_date, args.to_date)
        added, updated, total = sync_rows(args.csv, rows)
    except (ConfigError, AuthError, ApiError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Done: {added} new, {updated} updated, {total} total rows in {args.csv}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
