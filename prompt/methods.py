from prompt.slots import FiveSlots, canonical_json

COT_ADDENDUM = "# 作答方式\n先写 reasoning，再写 answer。\n"
REACT_ADDENDUM = (
    "# 动作协议\n每一步只输出一个 JSON 对象，键为 thought、action、action_input。"
    "action 只能是 echo_context 或 finish。echo_context 的 action_input 使用空对象。"
    "finish 的 action_input 是包含 reasoning 和 answer 的对象。\n"
)


def render_body(slots: FiveSlots, method: str) -> str:
    sections = [
        f"# 角色\n{slots.role}\n",
        f"# 任务\n{slots.task}\n",
        f"# 上下文\n{slots.context}\n",
        f"# 约束\n{slots.constraints}\n",
        f"# 输出格式\n{slots.output_format}\n",
    ]
    body = "\n".join(sections)
    if method == "zero_shot":
        return body
    if method == "few_shot":
        blocks = [f"输入：\n{item.input}\n输出：\n{item.output}" for item in slots.examples]
        addendum = "# 示例\n" + "\n\n".join(blocks) + "\n"
    elif method in {"cot", "self_consistency"}:
        addendum = COT_ADDENDUM
    elif method == "react":
        addendum = REACT_ADDENDUM
    else:
        raise ValueError(f"unknown method: {method}")
    return body + "\n" + addendum


def render_message(slots: FiveSlots, method: str, task: str, item: object, task_brief: str | None) -> list[dict]:
    context = slots.context
    if task == "distill":
        context = context.replace("{task_brief}", task_brief or "")
    context = context.replace("{item}", canonical_json(item))
    filled = FiveSlots(slots.role, slots.task, context, slots.constraints, slots.output_format, slots.examples)
    return [{"role": "user", "content": render_body(filled, method)}]
