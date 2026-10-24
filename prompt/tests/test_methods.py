from prompt.methods import render_body, render_message
from prompt.slots import Example, FiveSlots

BASE = FiveSlots("角色甲", "任务乙", "上下文{item}", "用短句。", "先写 reasoning，再写 answer。", [])
ZERO = (
    "# 角色\n角色甲\n\n"
    "# 任务\n任务乙\n\n"
    "# 上下文\n上下文{item}\n\n"
    "# 约束\n用短句。\n\n"
    "# 输出格式\n先写 reasoning，再写 answer。\n"
)


def test_zero_shot_matches_template():
    assert render_body(BASE, "zero_shot") == ZERO
    assert "# 示例" not in ZERO
    assert "# 作答方式" not in render_body(BASE, "zero_shot")
    assert "# 动作协议" not in render_body(BASE, "zero_shot")


def test_cot_and_self_consistency_share_addendum():
    cot = render_body(BASE, "cot")
    assert cot == render_body(BASE, "self_consistency")
    assert cot.endswith("# 作答方式\n先写 reasoning，再写 answer。\n")
    assert "\n\n# 作答方式\n" in cot


def test_few_shot_and_react_addenda():
    slots = FiveSlots(BASE.role, BASE.task, BASE.context, BASE.constraints, BASE.output_format, [
        Example('{"text":"甲"}', '{"reasoning":"依据已写在材料中。","answer":"keep"}'),
        Example('{"text":"乙"}', '{"reasoning":"依据已写在材料中。","answer":"drop"}'),
    ])
    text = render_body(slots, "few_shot")
    assert "# 示例\n输入：\n{\"text\":\"甲\"}\n输出：\n{\"reasoning\":\"依据已写在材料中。\",\"answer\":\"keep\"}\n\n输入：\n" in text
    react = render_body(BASE, "react")
    assert react.endswith(
        "# 动作协议\n每一步只输出一个 JSON 对象，键为 thought、action、action_input。"
        "action 只能是 echo_context 或 finish。echo_context 的 action_input 使用空对象。"
        "finish 的 action_input 是包含 reasoning 和 answer 的对象。\n"
    )


def test_render_message_fills_placeholders_without_mutating_slots():
    slots = FiveSlots(BASE.role, BASE.task, "任务说明：{task_brief}\n当前材料：{item}", BASE.constraints, BASE.output_format, [])
    message = render_message(slots, "zero_shot", "distill", {"text": "患者张三"}, "抽出 name。")
    assert message == [{"role": "user", "content": render_body(
        FiveSlots(slots.role, slots.task, "任务说明：抽出 name。\n当前材料：{\"text\":\"患者张三\"}", slots.constraints, slots.output_format, []),
        "zero_shot",
    )}]
    assert slots.context == "任务说明：{task_brief}\n当前材料：{item}"
