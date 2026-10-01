"""Per-player statistics computed from scraped ScoreRow data."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls
from statistics import mean, median, pstdev
from typing import Dict, List, Set, Tuple

from .models import ScoreRow

PERFECT_ROUND = 5000
ROUNDS_PER_GAME = 5


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
    rounds_tracked: int
    five_ks: int

    @property
    def five_k_rate(self) -> float:
        return self.five_ks / self.rounds_tracked if self.rounds_tracked else 0.0


def weekday_of(row: ScoreRow) -> int:
    """Monday is 0, Sunday is 6."""
    return date_cls.fromisoformat(row.challenge_date).weekday()


def weekday_rows(rows: List[ScoreRow]) -> List[ScoreRow]:
    """Drop Saturday and Sunday challenges."""
    return [r for r in rows if weekday_of(r) < 5]


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
        rounds = [score for r in player_rows for score in r.round_scores or ()]
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
                rounds_tracked=len(rounds),
                five_ks=sum(1 for score in rounds if score == PERFECT_ROUND),
            )
        )
    return sorted(stats, key=lambda s: s.average_score, reverse=True)


def average_by_weekday(rows: List[ScoreRow]) -> Dict[str, Dict[int, float]]:
    """Each player's average score per weekday (0=Monday), only for weekdays they played."""
    averages: Dict[str, Dict[int, float]] = {}
    for player_id, player_rows in group_by_player(rows).items():
        by_day: Dict[int, List[int]] = defaultdict(list)
        for row in player_rows:
            by_day[weekday_of(row)].append(row.total_score)
        averages[player_id] = {day: mean(scores) for day, scores in by_day.items()}
    return averages


def average_by_round(rows: List[ScoreRow]) -> Dict[str, List[float]]:
    """Each player's average score for round 1 through 5, from days with round data."""
    averages: Dict[str, List[float]] = {}
    for player_id, player_rows in group_by_player(rows).items():
        games = [r.round_scores for r in player_rows if r.round_scores and len(r.round_scores) == ROUNDS_PER_GAME]
        if games:
            averages[player_id] = [mean(game[i] for game in games) for i in range(ROUNDS_PER_GAME)]
    return averages


def rolling_mean(values: List[float], window: int) -> List[float]:
    """Trailing mean; the first few points average over however many values exist so far."""
    return [mean(values[max(0, i - window + 1) : i + 1]) for i in range(len(values))]


def head_to_head(rows: List[ScoreRow]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """(wins, shared_days) for every ordered player pair: how often a strictly beat b."""
    by_date: Dict[str, Dict[str, int]] = defaultdict(dict)
    for row in rows:
        by_date[row.challenge_date][row.player_id] = row.total_score

    records: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])
    for scores in by_date.values():
        for a, a_score in scores.items():
            for b, b_score in scores.items():
                if a != b:
                    records[(a, b)][1] += 1
                    records[(a, b)][0] += a_score > b_score
    return {pair: (wins, shared) for pair, (wins, shared) in records.items()}
