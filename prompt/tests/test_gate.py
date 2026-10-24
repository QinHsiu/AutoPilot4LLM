from prompt.gate import check_gate, parse_json_text

GOOD = {
    "role": "你是一名只看字段的清洗员",
    "task": "判断当前样本应当保留还是删除",
    "context": "当前样本：{item}",
    "constraints": "三个字段都是非空字符串时回答 keep。",
    "output_format": "先写 reasoning，再写 answer。",
    "examples": [],
}


def test_good_zero_shot_passes():
    result = check_gate(GOOD, "zero_shot", "clean", [])
    assert result.ok


def test_each_rejection_rule():
    cases = {
        "method_key": {**GOOD, "method": "cot"},
        "extra_key:note": {**GOOD, "note": "x"},
        "empty_field:role": {**GOOD, "role": "  "},
        "output_format": {**GOOD, "output_format": "先写 answer，再写 reasoning。"},
        "constraint:不要用术语": {**GOOD, "constraints": "不要用术语。用短句。"},
        "examples_must_be_empty": {**GOOD, "examples": [{"input": "a", "output": "b"}]},
        "missing_placeholder:{item}": {**GOOD, "context": "没有占位符"},
    }
    for reason, payload in cases.items():
        assert check_gate(payload, "zero_shot", "clean", []).reason == reason


def test_bie_de_is_allowed_and_blank_sentences_are_skipped():
    payload = {**GOOD, "constraints": "别的情况回答 drop。\n。"}
    assert check_gate(payload, "zero_shot", "clean", []).ok
    rejected = {**GOOD, "constraints": "别人来回答。"}
    assert check_gate(rejected, "zero_shot", "clean", []).reason == "constraint:别人来回答"


def test_few_shot_count_placeholder_and_overlap():
    demos = [{"input": '{"text":"甲"}', "output": '{"reasoning":"依据已写在材料中。","answer":{}}'}]
    short = {**GOOD, "context": "任务说明：{task_brief}\n当前材料：{item}", "examples": demos}
    assert check_gate(short, "few_shot", "distill", []).reason == "example_count"
    demos = demos + [{"input": '{"text":"乙"}', "output": '{"reasoning":"依据已写在材料中。","answer":{}}'}]
    ok = {**short, "examples": demos}
    assert check_gate(ok, "few_shot", "distill", [{"text": "丙"}]).ok
    assert check_gate(ok, "few_shot", "distill", [{"text": "甲"}]).reason == "example_overlaps_val"
    missing = {**ok, "context": "当前材料：{item}"}
    assert check_gate(missing, "few_shot", "distill", []).reason == "missing_placeholder:{task_brief}"


def test_fence_is_stripped_once():
    assert parse_json_text('```json\n{"role": "甲"}\n```') == {"role": "甲"}
    assert parse_json_text('```json\n{\n```') is None
