"""Per-player statistics computed from scraped ScoreRow data."""

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean, median, pstdev
from typing import Dict, List, Set

from .models import ScoreRow


@dataclass
class PlayerStats:
    player_id: str
    player_name: str
    games_played: int
    average_score: float
    median_score: float
    best_score: int
    worst_score: int
    score_stdev: float
    wins: int
    win_rate: float


def group_by_player(rows: List[ScoreRow]) -> Dict[str, List[ScoreRow]]:
    """Group rows by player_id."""
    grouped: Dict[str, List[ScoreRow]] = defaultdict(list)
    for row in rows:
        grouped[row.player_id].append(row)
    return grouped


def latest_name_by_player(rows: List[ScoreRow]) -> Dict[str, str]:
    """Each player's most recently scraped nickname, in case it changed."""
    names: Dict[str, str] = {}
    for row in sorted(rows, key=lambda r: r.scraped_at):
        names[row.player_id] = row.player_name
    return names


def compute_daily_winners(rows: List[ScoreRow]) -> Dict[str, Set[str]]:
    """The player_id(s) with the top score for each challenge date. Ties win jointly."""
    by_date: Dict[str, List[ScoreRow]] = defaultdict(list)
    for row in rows:
        by_date[row.challenge_date].append(row)

    winners: Dict[str, Set[str]] = {}
    for challenge_date, day_rows in by_date.items():
        top_score = max(r.total_score for r in day_rows)
        winners[challenge_date] = {r.player_id for r in day_rows if r.total_score == top_score}
    return winners


def compute_player_stats(rows: List[ScoreRow]) -> List[PlayerStats]:
    """One PlayerStats per player, sorted by average score descending."""
    grouped = group_by_player(rows)
    names = latest_name_by_player(rows)
    winners = compute_daily_winners(rows)

    stats = []
    for player_id, player_rows in grouped.items():
        scores = [r.total_score for r in player_rows]
        games_played = len(scores)
        wins = sum(1 for winner_ids in winners.values() if player_id in winner_ids)
        stats.append(
            PlayerStats(
                player_id=player_id,
                player_name=names.get(player_id, ""),
                games_played=games_played,
                average_score=mean(scores),
                median_score=median(scores),
                best_score=max(scores),
                worst_score=min(scores),
                score_stdev=pstdev(scores) if games_played > 1 else 0.0,
                wins=wins,
                win_rate=wins / games_played,
            )
        )
    return sorted(stats, key=lambda s: s.average_score, reverse=True)
