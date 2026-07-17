"""Load the GeoGuessr session cookie from the environment or a .env file."""

import os
from pathlib import Path
from typing import Dict

COOKIE_ENV_VAR = "GEOGUESSR_NCFA"


class ConfigError(Exception):
    pass


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Ignores blanks and # comments."""
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_ncfa_cookie(env_file: Path) -> str:
    """Return the _ncfa cookie value, preferring the real environment."""
    cookie = os.environ.get(COOKIE_ENV_VAR) or parse_env_file(env_file).get(COOKIE_ENV_VAR)
    if not cookie:
        raise ConfigError(
            f"No GeoGuessr session cookie found. Set {COOKIE_ENV_VAR} in your "
            f"environment or in {env_file}. See README.md for how to copy the "
            "_ncfa cookie from your browser."
        )
    return cookie
