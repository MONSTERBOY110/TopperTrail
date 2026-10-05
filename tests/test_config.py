from pathlib import Path

from toppertrail.config import load_settings


def test_env_overrides_dotenv(tmp_path: Path):
    (tmp_path / ".env").write_text(
        "SERPAPI_API_KEY=fromfile\nTOPPERTRAIL_BUDGET=50\n", encoding="utf-8"
    )
    s = load_settings(env={"SERPAPI_API_KEY": "fromenv"}, cwd=tmp_path)
    assert s.api_key == "fromenv"
    assert s.budget_cap == 50
    assert s.replay is False
    assert s.home == tmp_path / ".toppertrail"
    assert s.fixtures == tmp_path / "fixtures"


def test_replay_flag_and_missing_key(tmp_path: Path):
    s = load_settings(env={"TOPPERTRAIL_REPLAY": "1"}, cwd=tmp_path)
    assert s.replay is True
    assert s.api_key is None
    assert s.budget_cap == 230
