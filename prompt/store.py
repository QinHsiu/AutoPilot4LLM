import json
from pathlib import Path


def make_run_dir(root, task: str, method: str, now) -> Path:
    stamp = now.strftime("%Y%m%dT%H%M%S")
    path = Path(root) / task / f"{method}-{stamp}"
    suffix = 2
    while path.exists():
        path = Path(root) / task / f"{method}-{stamp}-{suffix}"
        suffix += 1
    path.mkdir(parents=True)
    return path


def append_version(run_dir, record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with (Path(run_dir) / "versions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_run(run_dir, record: dict) -> None:
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    (Path(run_dir) / "run.json").write_text(text + "\n", encoding="utf-8")
