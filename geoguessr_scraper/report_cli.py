"""Command line entry point: print player statistics and save score charts."""

import argparse
import sys
from pathlib import Path
from typing import List

from .stats import PlayerStats, compute_player_stats
from .store import load_rows

HEADER = (
    f"{'Player':<20}{'Games':>7}{'Avg':>8}{'Median':>8}"
    f"{'Best':>8}{'Worst':>8}{'Wins':>7}{'Win %':>8}"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show player statistics and save score charts from scores.csv."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("scores.csv"),
        help="Path to the scores CSV to read (default: scores.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("plots"),
        help="Directory to save charts into (default: plots)",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Only print the statistics table; skip generating charts",
    )
    return parser


def format_stats_table(stats: List[PlayerStats]) -> str:
    lines = [HEADER, "-" * len(HEADER)]
    for s in stats:
        lines.append(
            f"{s.player_name:<20}{s.games_played:>7}{s.average_score:>8.0f}"
            f"{s.median_score:>8.0f}{s.best_score:>8}{s.worst_score:>8}"
            f"{s.wins:>7}{s.win_rate * 100:>7.0f}%"
        )
    return "\n".join(lines)


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)

    rows = list(load_rows(args.csv).values())
    if not rows:
        print(f"No data in {args.csv}. Run scrape.py first.", file=sys.stderr)
        return 1

    stats = compute_player_stats(rows)
    print(format_stats_table(stats))

    if not args.no_plots:
        from .plots import generate_all_plots  # deferred: matplotlib import is slow

        written = generate_all_plots(rows, stats, args.output_dir)
        print(f"\nSaved {len(written)} charts to {args.output_dir}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
