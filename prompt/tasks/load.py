import importlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from prompt.errors import PreflightError
from prompt.slots import Example, FiveSlots, canonical_json

ROOT = Path(__file__).resolve().parent
PACKS = ("distill", "clean", "govern", "train_analysis", "badcase")


@dataclass
class TaskPack:
    name: str
    slots: FiveSlots
    task_brief: str | None
    val: list[dict]
    score_one: object


def assert_no_overlap(examples, rows) -> None:
    canonical_inputs = {canonical_json(row["input"]) for row in rows}
    for example in examples:
        if example.input in canonical_inputs:
            raise PreflightError("example overlaps val")


def read_val(path: Path) -> list[dict]:
    if not path.exists():
        raise PreflightError("missing field: val")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PreflightError("missing field: val") from exc
        if not isinstance(row, dict):
            raise PreflightError("missing field: val")
        for key in ("id", "input", "gold"):
            if key not in row:
                raise PreflightError(f"missing field: {key}")
        rows.append(row)
    if not rows:
        raise PreflightError("empty val")
    return rows


def load_pack(name: str, val_path: str | None = None) -> TaskPack:
    if name not in PACKS:
        raise PreflightError(f"unknown task: {name}")
    data = yaml.safe_load((ROOT / name / "seed.yaml").read_text(encoding="utf-8"))
    examples = [Example(input=item["input"], output=item["output"]) for item in data["examples"]]
    slots = FiveSlots(data["role"], data["task"], data["context"], data["constraints"], data["output_format"], examples)
    val = read_val(Path(val_path) if val_path else ROOT / name / "val.jsonl")
    assert_no_overlap(examples, val)
    score_one = importlib.import_module(f"prompt.tasks.{name}.metric").score_one
    return TaskPack(name, slots, data.get("task_brief"), val, score_one)
