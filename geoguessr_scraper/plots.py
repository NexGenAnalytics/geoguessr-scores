"""Matplotlib charts summarizing scraped Daily Challenge scores."""

import matplotlib

matplotlib.use("Agg")  # headless: these scripts save PNGs, they don't need a display

import matplotlib.pyplot as plt
from datetime import date as date_cls
from pathlib import Path
from typing import Dict, List, Tuple

from .models import ScoreRow
from .stats import (
    ROUNDS_PER_GAME,
    PlayerStats,
    average_by_round,
    average_by_weekday,
    group_by_player,
    head_to_head,
    rolling_mean,
)

COLOR_MAP = plt.get_cmap("tab10")
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ROLLING_WINDOW = 5


def _player_colors(stats: List[PlayerStats]) -> Dict[str, Tuple[float, float, float, float]]:
    """A consistent color per player_id, shared across all charts."""
    return {stat.player_id: COLOR_MAP(i % 10) for i, stat in enumerate(stats)}


def _save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _show_no_data(ax, message: str) -> None:
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, color="gray")
    ax.set_xticks([])
    ax.set_yticks([])


def _grouped_bars(ax, stats: List[PlayerStats], values_by_player: Dict[str, List[float]], labels: List[str]) -> None:
    """One cluster per label, one bar per player inside each cluster."""
    colors = _player_colors(stats)
    players = [s for s in stats if s.player_id in values_by_player]
    width = 0.8 / max(len(players), 1)
    for i, stat in enumerate(players):
        offsets = [x + (i - (len(players) - 1) / 2) * width for x in range(len(labels))]
        ax.bar(offsets, values_by_player[stat.player_id], width * 0.92, label=stat.player_name, color=colors[stat.player_id])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.margins(y=0.15)  # headroom so the legend row sits above the bars
    ax.legend(loc="upper center", ncol=len(players))
    ax.grid(True, axis="y", alpha=0.3)


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
    _save(fig, path)


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
    _save(fig, path)


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
    _save(fig, path)


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
    _save(fig, path)


def plot_rolling_average(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Each player's trailing average over their last few games, which smooths out daily noise."""
    colors = _player_colors(stats)
    grouped = group_by_player(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    for stat in stats:
        ordered = sorted(grouped[stat.player_id], key=lambda r: r.challenge_date)
        dates = [date_cls.fromisoformat(r.challenge_date) for r in ordered]
        smoothed = rolling_mean([r.total_score for r in ordered], ROLLING_WINDOW)
        ax.plot(dates, smoothed, linewidth=2, label=stat.player_name, color=colors[stat.player_id])

    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.set_title(f"{ROLLING_WINDOW}-Game Rolling Average")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate(rotation=45)
    _save(fig, path)


def plot_day_of_week(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Average score per weekday per player."""
    averages = average_by_weekday(rows)
    played_days = {day for by_day in averages.values() for day in by_day}
    days = list(range(7 if played_days & {5, 6} else 5))
    values = {pid: [by_day.get(day, 0) for day in days] for pid, by_day in averages.items()}

    fig, ax = plt.subplots(figsize=(10, 6))
    _grouped_bars(ax, stats, values, [WEEKDAY_NAMES[d] for d in days])
    ax.set_ylabel("Average Score")
    ax.set_title("Average Score by Day of the Week")
    _save(fig, path)


def plot_head_to_head(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Grid of how often the row player beat the column player on days both played."""
    records = head_to_head(rows)
    names = [s.player_name for s in stats]
    ids = [s.player_id for s in stats]

    fig, ax = plt.subplots(figsize=(2 + 1.6 * len(ids), 1.5 + 1.4 * len(ids)))
    grid = [[float("nan")] * len(ids) for _ in ids]
    for i, a in enumerate(ids):
        for j, b in enumerate(ids):
            wins, shared = records.get((a, b), (0, 0))
            if a == b or not shared:
                continue
            grid[i][j] = 100 * wins / shared
            ax.text(j, i, f"{grid[i][j]:.0f}%\n({wins}/{shared})", ha="center", va="center", fontsize=9)

    image = ax.imshow(grid, cmap="RdBu", vmin=0, vmax=100)
    fig.colorbar(image, ax=ax, label="% of shared days won")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("Opponent")
    ax.set_title("Head-to-Head: how often each row beat each column")
    _save(fig, path)


def plot_five_ks(stats: List[PlayerStats], path: Path) -> None:
    """Number of perfect 5000-point rounds per player, labeled with rounds tracked."""
    colors = _player_colors(stats)
    tracked = sorted((s for s in stats if s.rounds_tracked), key=lambda s: s.five_k_rate, reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Perfect Rounds (5ks) by Player")
    if not tracked:
        _show_no_data(ax, "No round-by-round data yet. Run scrape.py to start collecting it.")
        _save(fig, path)
        return

    bars = ax.bar(
        [s.player_name for s in tracked],
        [s.five_ks for s in tracked],
        width=0.6,
        color=[colors[s.player_id] for s in tracked],
    )
    ax.bar_label(bars, labels=[f"{s.five_k_rate:.0%} of {s.rounds_tracked} rounds" for s in tracked], padding=3)
    ax.set_ylabel("5ks")
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.grid(True, axis="y", alpha=0.3)
    _save(fig, path)


def plot_round_averages(rows: List[ScoreRow], stats: List[PlayerStats], path: Path) -> None:
    """Average score for each round number, to spot a player's weakest round."""
    averages = average_by_round(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Average Score by Round")
    if not averages:
        _show_no_data(ax, "No round-by-round data yet. Run scrape.py to start collecting it.")
        _save(fig, path)
        return

    _grouped_bars(ax, stats, averages, [f"Round {i + 1}" for i in range(ROUNDS_PER_GAME)])
    ax.axhline(5000, color="gray", linestyle="--", linewidth=1)
    ax.set_ylabel("Average Score")
    _save(fig, path)


def generate_all_plots(rows: List[ScoreRow], stats: List[PlayerStats], output_dir: Path) -> List[Path]:
    """Write every chart into output_dir and return the paths written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plots = [
        ("score_trends.png", plot_score_trends, (rows, stats)),
        ("score_distribution.png", plot_score_distribution, (rows, stats)),
        ("average_scores.png", plot_average_scores, (stats,)),
        ("wins.png", plot_wins, (stats,)),
        ("rolling_average.png", plot_rolling_average, (rows, stats)),
        ("day_of_week.png", plot_day_of_week, (rows, stats)),
        ("head_to_head.png", plot_head_to_head, (rows, stats)),
        ("five_ks.png", plot_five_ks, (stats,)),
        ("round_averages.png", plot_round_averages, (rows, stats)),
    ]
    written = []
    for filename, plot_fn, plot_args in plots:
        path = output_dir / filename
        plot_fn(*plot_args, path)
        written.append(path)
    return written
