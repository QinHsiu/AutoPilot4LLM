from prompt.slots import FiveSlots, canonical_json, slots_from_dict, slots_to_dict, working_copy


def test_canonical_json_sorts_keys_and_keeps_chinese():
    text = canonical_json({"b": 1, "a": "患者"})
    assert text == '{"a":"患者","b":1}'


def test_slots_round_trip_and_working_copy():
    slots = FiveSlots("角色", "判断样本", "当前样本：{item}", "回答 keep。", "先写 reasoning，再写 answer。", [])
    copied = slots_from_dict(slots_to_dict(slots))
    assert copied == slots
    few = working_copy(slots, "few_shot")
    assert few.examples == []
    assert working_copy(slots, "zero_shot").examples == []
