"""Normalize GeoGuessr API responses into ScoreRow records.

Verified against the live API (2026-07): a month-summary entry looks like
{"day": 16, "dayOfWeek": 4, "totalScore": 23484, "medal": "Gold", ...}, with
no date string, token, time, or distance field. Days that were played but
not finished, or where a streak freeze was used, have totalScore: null and
are treated as unplayed. Key lookups still try a couple of alternate names
in case GeoGuessr changes the field names.
"""

from datetime import date as date_cls
from typing import Dict, List, Optional, Tuple

from .models import ScoreRow

DATE_KEYS = ("date", "dateStr", "challengeDate")
SCORE_KEYS = ("totalScore", "score")
TIME_KEYS = ("totalTime", "totalTimeSeconds")
DISTANCE_KEYS = ("totalDistanceInMeters", "totalDistance")
TOKEN_KEYS = ("token", "challengeToken")
ID_KEYS = ("id", "userId")
NAME_KEYS = ("nick", "name")


def _first_present(source: dict, keys: Tuple[str, ...]):
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _score_amount(value: object) -> Optional[int]:
    """A score is a plain int in some shapes and {"amount": "123"} in others."""
    if isinstance(value, dict):
        value = value.get("amount")
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def profile_identity(payload: object) -> Optional[Tuple[str, str]]:
    """Extract (player_id, player_name) from a GET /profiles/ response."""
    user = payload.get("user") if isinstance(payload, dict) else None
    if not isinstance(user, dict):
        return None
    player_id = _first_present(user, ID_KEYS)
    if not player_id:
        return None
    return str(player_id), str(_first_present(user, NAME_KEYS) or "")


def iter_month_entries(payload: object) -> List[dict]:
    """Pull the list of day entries out of a month-summary response."""
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        for key in ("results", "days", "entries", "items", "summary"):
            value = payload.get(key)
            if isinstance(value, list):
                return [entry for entry in value if isinstance(entry, dict)]
    return []


def score_row_from_month_entry(
    entry: dict, year: int, month: int, player_id: str, player_name: str, scraped_at: str
) -> Optional[ScoreRow]:
    """Build a ScoreRow for one played day; returns None for unplayed days."""
    score = _score_amount(_first_present(entry, SCORE_KEYS))
    if score is None:
        return None  # not played, incomplete, or a streak freeze was used

    full_date = _first_present(entry, DATE_KEYS)
    if full_date:
        date_str = str(full_date)[:10]
    else:
        day = entry.get("day")
        if not isinstance(day, int):
            return None
        date_str = date_cls(year, month, day).isoformat()

    return ScoreRow(
        challenge_date=date_str,
        challenge_token=str(_first_present(entry, TOKEN_KEYS) or ""),
        player_id=player_id,
        player_name=player_name,
        total_score=score,
        total_time_seconds=_first_present(entry, TIME_KEYS),
        total_distance=_first_present(entry, DISTANCE_KEYS),
        scraped_at=scraped_at,
    )


def daily_tokens_by_date(challenges: List[object]) -> Dict[str, str]:
    """Map YYYY-MM-DD to challenge token from today/previous daily-challenge responses."""
    tokens: Dict[str, str] = {}
    for challenge in challenges:
        if isinstance(challenge, dict) and challenge.get("date") and challenge.get("token"):
            tokens[str(challenge["date"])[:10]] = str(challenge["token"])
    return tokens


def finished_player(game: object) -> Optional[dict]:
    """The player block of a finished game from GET /challenges/{token}/game.

    Verified against the live API (2026-10): {"state": "finished", "player": {"id",
    "totalTime", "totalDistanceInMeters", "guesses": [{"roundScoreInPoints"}, ...]}}.
    """
    if not isinstance(game, dict) or game.get("state") != "finished":
        return None
    player = game.get("player")
    return player if isinstance(player, dict) else None


def round_scores_from_result(player: dict) -> Optional[Tuple[int, ...]]:
    guesses = player.get("guesses")
    if not isinstance(guesses, list) or not guesses:
        return None
    scores = [_score_amount(g.get("roundScoreInPoints", g.get("roundScore"))) for g in guesses]
    return None if None in scores else tuple(scores)
