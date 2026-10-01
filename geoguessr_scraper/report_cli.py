"""Command line entry point: print player statistics and save score charts."""

import argparse
import sys
from pathlib import Path
from typing import List

from .stats import PlayerStats, compute_player_stats, weekday_rows
from .store import load_rows

HEADER = (
    f"{'Player':<20}{'Games':>7}{'Avg':>8}{'Median':>8}"
    f"{'Best':>8}{'Worst':>8}{'Wins':>7}{'Win %':>8}{'5ks':>6}{'5k %':>7}"
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
    parser.add_argument(
        "--include-weekends",
        action="store_true",
        help="Include Saturday and Sunday challenges in the charts (excluded by default)",
    )
    return parser


def _five_k_percent(stat: PlayerStats) -> str:
    return f"{stat.five_k_rate * 100:.0f}%" if stat.rounds_tracked else "-"


def format_stats_table(stats: List[PlayerStats]) -> str:
    lines = [HEADER, "-" * len(HEADER)]
    for s in stats:
        lines.append(
            f"{s.player_name:<20}{s.games_played:>7}{s.average_score:>8.0f}"
            f"{s.median_score:>8.0f}{s.best_score:>8}{s.worst_score:>8}"
            f"{s.wins:>7}{s.win_rate * 100:>7.0f}%{s.five_ks:>6}{_five_k_percent(s):>7}"
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

        plot_rows = rows if args.include_weekends else weekday_rows(rows)
        if not plot_rows:
            print("\nNo weekday games to chart. Use --include-weekends to chart weekends.")
            return 0
        written = generate_all_plots(plot_rows, compute_player_stats(plot_rows), args.output_dir)
        scope = "all days" if args.include_weekends else "weekdays only"
        print(f"\nSaved {len(written)} charts ({scope}) to {args.output_dir}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
