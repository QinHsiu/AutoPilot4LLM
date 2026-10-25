import json

from prompt.runner import run_validation
from prompt.slots import FiveSlots
from prompt.tasks.clean.metric import score_one as clean_score
from prompt.tests.fakes import ScriptedClient

SLOTS = FiveSlots("角色", "判断当前样本应当保留还是删除", "当前样本：{item}", "回答 keep。", "先写 reasoning，再写 answer。", [])
ROW = {"id": "c1", "input": {"name": "张三", "sex": "男", "symptom": "发热两天"}, "gold": "keep"}


def answer(value):
    return json.dumps({"reasoning": "依据已写在材料中。", "answer": value}, ensure_ascii=False)


def test_parse_failure_is_a_miss_and_match_passes():
    client = ScriptedClient(["nope", answer("keep")])
    results = run_validation(SLOTS, "zero_shot", "clean", None, [ROW, ROW], clean_score, client, 0, 5, 4)
    assert results[0].reason == "parse_error" and results[0].passed is False
    assert results[1].passed and results[1].answer == "keep"


def test_self_consistency_majority_tie_and_total_failure():
    client = ScriptedClient([answer("keep"), answer("drop"), answer("keep"), answer("drop"), answer("keep")])
    result = run_validation(SLOTS, "self_consistency", "clean", None, [ROW], clean_score, client, 0, 5, 4)[0]
    assert result.answer == "keep" and result.passed
    tie = ScriptedClient([answer("drop"), answer("keep")])
    tied = run_validation(SLOTS, "self_consistency", "clean", None, [ROW], clean_score, tie, 0, 2, 4)[0]
    assert tied.answer == "drop"
    blank = ScriptedClient(["nope", "nope"])
    missed = run_validation(SLOTS, "self_consistency", "clean", None, [ROW], clean_score, blank, 0, 2, 4)[0]
    assert missed.reason == "parse_error"


def test_react_finish_and_unfinished():
    echo = json.dumps({"thought": "看样本", "action": "echo_context", "action_input": {}}, ensure_ascii=False)
    finish = json.dumps({"thought": "结束", "action": "finish", "action_input": {"reasoning": "依据已写在材料中。", "answer": "keep"}}, ensure_ascii=False)
    client = ScriptedClient([echo, finish])
    result = run_validation(SLOTS, "react", "clean", None, [ROW], clean_score, client, 0, 5, 4)[0]
    assert result.passed
    assert client.calls[1]["messages"][1]["content"] == echo
    assert client.calls[1]["messages"][-1]["content"].startswith("观察：")
    stuck = ScriptedClient([echo, echo, echo, echo])
    unfinished = run_validation(SLOTS, "react", "clean", None, [ROW], clean_score, stuck, 0, 5, 4)[0]
    assert unfinished.reason == "react_unfinished"
