import json
from datetime import datetime

import pytest

from prompt.config import Config
from prompt.errors import PreflightError
from prompt.evolve import evolver_messages, evolve
from prompt.llm import LlmError
from prompt.slots import slots_to_dict, working_copy
from prompt.tasks.load import load_pack
from prompt.tests.fakes import ScriptedClient

CONFIG = Config(base_url="http://example.invalid/v1", model="demo", max_iters=2)
NOW = datetime(2026, 10, 24, 22, 13, 0)


def answer(value):
    return json.dumps({"reasoning": "依据已写在材料中。", "answer": value}, ensure_ascii=False)


def test_meta_prompt_replaces_placeholders_once():
    pack = load_pack("clean")
    slots = working_copy(pack.slots, "zero_shot")
    message = evolver_messages("zero_shot", slots, [])[0]["content"]
    assert "你是一名只改写提示词五格的修订员" in message
    assert "{slots}" not in message
    assert "{item}" in message


def test_missing_key_does_not_call_client(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = ScriptedClient([])
    with pytest.raises(PreflightError, match="missing env: OPENAI_API_KEY"):
        evolve("clean", "zero_shot", CONFIG, client=client, clock=lambda: NOW, runs_root=tmp_path)
    assert client.calls == []
    assert list(tmp_path.iterdir()) == []


def test_gate_reject_then_perfect(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    pack = load_pack("clean")
    good = json.dumps(slots_to_dict(working_copy(pack.slots, "zero_shot")), ensure_ascii=False)
    bad = json.dumps({"method": "cot"})
    replies = [answer("keep")] * 4 + [bad, good] + [answer(row["gold"]) for row in pack.val]
    client = ScriptedClient(replies)
    result = evolve("clean", "zero_shot", CONFIG, client=client, clock=lambda: NOW, runs_root=tmp_path)
    assert result.stop_reason == "perfect_score"
    assert result.best_passed == 4
    assert [call["temperature"] for call in client.calls] == [0, 0, 0, 0, 0.7, 0.7, 0, 0, 0, 0]


def test_no_improvement_stops(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    pack = load_pack("clean")
    good = json.dumps(slots_to_dict(working_copy(pack.slots, "zero_shot")), ensure_ascii=False)
    three_of_four = [answer("keep"), answer("drop"), answer("drop"), answer("drop")]
    seed = [answer("keep")] * 4
    client = ScriptedClient(seed + [good] + three_of_four + [good] + three_of_four)
    config = Config(CONFIG.base_url, CONFIG.model, max_iters=3)
    result = evolve("clean", "zero_shot", config, client=client, clock=lambda: NOW, runs_root=tmp_path)
    assert result.stop_reason == "no_improvement"
    assert result.best_passed == 3
    lines = (tmp_path / "clean" / "zero_shot-20261024T221300" / "versions.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[-1])["accepted"] is False


def test_seed_llm_error_returns_null_best(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = ScriptedClient([LlmError("down")])
    result = evolve("clean", "zero_shot", CONFIG, client=client, clock=lambda: NOW, runs_root=tmp_path)
    assert result.stop_reason == "seed_score_failed"
    assert result.best_slots is None
    assert result.best_passed is None


def test_gate_rejects_exhaust_iters(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    bad = json.dumps({"method": "cot"})
    client = ScriptedClient([answer("keep")] * 4 + [bad, bad])
    result = evolve("clean", "zero_shot", CONFIG, client=client, clock=lambda: NOW, runs_root=tmp_path)
    assert result.stop_reason == "max_iters"
    assert result.best_passed == 2


def test_task_brief_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(PreflightError, match="distill"):
        evolve("clean", "zero_shot", CONFIG, task_brief="别的任务", clock=lambda: NOW, runs_root=tmp_path)
    with pytest.raises(PreflightError, match="val_path"):
        evolve("distill", "zero_shot", CONFIG, task_brief="抽出 age。", clock=lambda: NOW, runs_root=tmp_path)
