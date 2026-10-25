from dataclasses import dataclass
from pathlib import Path

import yaml

from prompt.errors import PreflightError


@dataclass
class Config:
    base_url: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    max_iters: int = 5
    temperature: float = 0
    evolver_temperature: float = 0.7
    self_consistency_n: int = 5
    react_max_steps: int = 4
    timeout_s: int = 60


def _or_default(data: dict, key: str, default):
    value = data.get(key)
    if value is None:
        return default
    return value


def load_config(path: str) -> Config:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PreflightError("missing field: config") from exc
    if not isinstance(data, dict):
        raise PreflightError("missing field: config")
    if not data.get("base_url"):
        raise PreflightError("missing field: base_url")
    if not data.get("model"):
        raise PreflightError("missing field: model")
    return Config(
        base_url=data["base_url"],
        model=data["model"],
        api_key_env=_or_default(data, "api_key_env", "OPENAI_API_KEY"),
        max_iters=_or_default(data, "max_iters", 5),
        temperature=_or_default(data, "temperature", 0),
        evolver_temperature=_or_default(data, "evolver_temperature", 0.7),
        self_consistency_n=_or_default(data, "self_consistency_n", 5),
        react_max_steps=_or_default(data, "react_max_steps", 4),
        timeout_s=_or_default(data, "timeout_s", 60),
    )


def config_public(config: Config) -> dict:
    return {
        "base_url": config.base_url,
        "model": config.model,
        "api_key_env": config.api_key_env,
        "max_iters": config.max_iters,
        "temperature": config.temperature,
        "evolver_temperature": config.evolver_temperature,
        "self_consistency_n": config.self_consistency_n,
        "react_max_steps": config.react_max_steps,
        "timeout_s": config.timeout_s,
    }
