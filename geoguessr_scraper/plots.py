"""Matplotlib charts summarizing scraped Daily Challenge scores."""

import matplotlib

matplotlib.use("Agg")  # headless: these scripts save PNGs, they don't need a display

import matplotlib.pyplot as plt
from datetime import date as date_cls
from pathlib import Path
from typing import Dict, List, Tuple

from .models import ScoreRow
from .stats import PlayerStats, group_by_player

COLOR_MAP = plt.get_cmap("tab10")


def _player_colors(stats: List[PlayerStats]) -> Dict[str, Tuple[float, float, float, float]]:
    """A consistent color per player_id, shared across all charts."""
    return {stat.player_id: COLOR_MAP(i % 10) for i, stat in enumerate(stats)}


def plot_score_trends(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Line chart of each player's score over time."""
    colors = _player_colors(stats)
    grouped = group_by_player(rows)
    names = {stat.player_id: stat.player_name for stat in stats}

    fig, ax = plt.subplots(figsize=(10, 6))
    for player_id, player_rows in grouped.items():
        ordered = sorted(player_rows, key=lambda r: r.challenge_date)
        dates = [date_cls.fromisoformat(r.challenge_date) for r in ordered]
        scores = [r.total_score for r in ordered]
        ax.plot(dates, scores, marker="o", label=names.get(player_id, player_id), color=colors[player_id])

    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.set_title("Daily Challenge Scores Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_score_distribution(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Box plot of each player's score spread."""
    colors = _player_colors(stats)
    grouped = group_by_player(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    box_data = [[r.total_score for r in grouped[stat.player_id]] for stat in stats]
    box = ax.boxplot(box_data, tick_labels=[stat.player_name for stat in stats], patch_artist=True)
    for patch, stat in zip(box["boxes"], stats):
        patch.set_facecolor(colors[stat.player_id])
        patch.set_alpha(0.6)

    ax.set_ylabel("Score")
    ax.set_title("Score Distribution by Player")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_average_scores(stats: List[PlayerStats], path: Path) -> None:
    """Bar chart of average score per player, ranked highest first."""
    colors = _player_colors(stats)
    ranked = sorted(stats, key=lambda s: s.average_score, reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        [s.player_name for s in ranked],
        [s.average_score for s in ranked],
        yerr=[s.score_stdev for s in ranked],
        capsize=4,
        color=[colors[s.player_id] for s in ranked],
    )
    ax.set_ylabel("Average Score")
    ax.set_title("Average Score by Player")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_wins(stats: List[PlayerStats], path: Path) -> None:
    """Bar chart of how many days each player had the top score (ties count for all)."""
    colors = _player_colors(stats)
    ranked = sorted(stats, key=lambda s: s.wins, reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        [s.player_name for s in ranked],
        [s.wins for s in ranked],
        color=[colors[s.player_id] for s in ranked],
    )
    ax.set_ylabel("Days Won")
    ax.set_title("Daily Wins by Player (ties count for everyone tied)")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def generate_all_plots(rows: List[ScoreRow], stats: List[PlayerStats], output_dir: Path) -> List[Path]:
    """Write every chart into output_dir and return the paths written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plots = [
        ("score_trends.png", plot_score_trends, (rows, stats)),
        ("score_distribution.png", plot_score_distribution, (rows, stats)),
        ("average_scores.png", plot_average_scores, (stats,)),
        ("wins.png", plot_wins, (stats,)),
    ]
    written = []
    for filename, plot_fn, plot_args in plots:
        path = output_dir / filename
        plot_fn(*plot_args, path)
        written.append(path)
    return written
