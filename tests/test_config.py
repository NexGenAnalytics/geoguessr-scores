import pytest

from geoguessr_scraper.config import ConfigError, load_ncfa_cookie, parse_env_file


def test_parse_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n"
        "\n"
        "GEOGUESSR_NCFA=abc123\n"
        "QUOTED='hello'\n"
        "not a kv line\n",
        encoding="utf-8",
    )
    values = parse_env_file(env)
    assert values["GEOGUESSR_NCFA"] == "abc123"
    assert values["QUOTED"] == "hello"


def test_env_var_takes_precedence(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEOGUESSR_NCFA=from-file\n", encoding="utf-8")
    monkeypatch.setenv("GEOGUESSR_NCFA", "from-env")
    assert load_ncfa_cookie(env) == "from-env"


def test_falls_back_to_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEOGUESSR_NCFA", raising=False)
    env = tmp_path / ".env"
    env.write_text("GEOGUESSR_NCFA=from-file\n", encoding="utf-8")
    assert load_ncfa_cookie(env) == "from-file"


def test_missing_cookie_raises_helpful_error(tmp_path, monkeypatch):
    monkeypatch.delenv("GEOGUESSR_NCFA", raising=False)
    with pytest.raises(ConfigError, match="_ncfa"):
        load_ncfa_cookie(tmp_path / ".env")
