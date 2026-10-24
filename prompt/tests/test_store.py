import json
from datetime import datetime

from prompt.store import append_version, make_run_dir, write_run


def test_run_dir_collision_and_jsonl(tmp_path):
    now = datetime(2026, 10, 24, 22, 13, 0)
    first = make_run_dir(tmp_path, "clean", "zero_shot", now)
    second = make_run_dir(tmp_path, "clean", "zero_shot", now)
    assert first.name == "zero_shot-20261024T221300"
    assert second.name == "zero_shot-20261024T221300-2"
    append_version(first, {"version": 0, "parent": None, "accepted": True, "kind": "seed"})
    write_run(first, {"stop_reason": "perfect_score", "best_version": 0})
    line = json.loads((first / "versions.jsonl").read_text(encoding="utf-8"))
    assert line["kind"] == "seed"
    assert json.loads((first / "run.json").read_text(encoding="utf-8"))["stop_reason"] == "perfect_score"
