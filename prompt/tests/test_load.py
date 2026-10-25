import json
from pathlib import Path

import pytest

from prompt.errors import PreflightError
from prompt.slots import canonical_json
from prompt.tasks.load import assert_no_overlap, load_pack


def test_bundled_packs_have_four_rows_and_placeholders():
    distill = load_pack("distill")
    assert distill.task_brief == "抽出 name、sex、symptom。name 是姓名，sex 是性别，symptom 是症状。"
    assert "{task_brief}" in distill.slots.context and "{item}" in distill.slots.context
    assert len(distill.val) == 4
    assert len(distill.slots.examples) == 2
    for name in ("clean", "govern", "train_analysis", "badcase"):
        pack = load_pack(name)
        assert len(pack.val) == 4
        assert "{item}" in pack.slots.context
        assert pack.task_brief is None


def test_val_json_is_canonical_and_examples_do_not_overlap():
    pack = load_pack("clean")
    raw = Path("prompt/tasks/clean/val.jsonl").read_text(encoding="utf-8").splitlines()
    for line, row in zip(raw, pack.val):
        assert line == canonical_json(row)
    assert pack.score_one("keep", "keep")


def test_overlap_and_bad_val_raise():
    with pytest.raises(PreflightError, match="example overlaps val"):
        assert_no_overlap([type("E", (), {"input": '{"a":1}'})()], [{"input": {"a": 1}}])
    with pytest.raises(PreflightError, match="unknown task"):
        load_pack("nope")
