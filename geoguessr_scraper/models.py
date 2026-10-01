"""Data types shared across the scraper."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ScoreRow:
    """One player's result for one Daily Challenge."""

    challenge_date: str  # YYYY-MM-DD (UTC)
    challenge_token: str
    player_id: str
    player_name: str
    total_score: int
    total_time_seconds: Optional[int]
    total_distance: Optional[float]  # as reported by GeoGuessr; units vary by endpoint
    scraped_at: str  # ISO 8601 UTC
    round_scores: Optional[Tuple[int, ...]] = None  # only available for the last ~7 days

    @property
    def key(self) -> tuple:
        return (self.challenge_date, self.player_id)
