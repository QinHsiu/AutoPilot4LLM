from pathlib import Path

import pytest

from prompt.config import config_public, load_config
from prompt.errors import PreflightError


def test_defaults_and_public_copy(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("base_url: http://example.invalid/v1\nmodel: demo\n", encoding="utf-8")
    config = load_config(str(path))
    assert config.api_key_env == "OPENAI_API_KEY"
    assert config.max_iters == 5
    assert config.temperature == 0
    assert config.evolver_temperature == 0.7
    assert config.self_consistency_n == 5
    assert config.react_max_steps == 4
    assert config.timeout_s == 60
    public = config_public(config)
    assert public["model"] == "demo"
    assert "api_key" not in public


def test_missing_required_field(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("model: demo\n", encoding="utf-8")
    with pytest.raises(PreflightError, match="missing field: base_url"):
        load_config(str(path))
