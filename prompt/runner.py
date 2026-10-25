from dataclasses import dataclass

from prompt.gate import parse_json_text
from prompt.methods import render_message
from prompt.slots import canonical_json

ANSWER_TYPES = {
    "distill": dict,
    "clean": str,
    "govern": str,
    "train_analysis": list,
    "badcase": str,
}


@dataclass
class ItemResult:
    id: str
    input: object
    gold: object
    answer: object
    passed: bool
    reason: str


def failure_payload(results: list[ItemResult]) -> list[dict]:
    payload = []
    for result in results:
        if result.passed:
            continue
        payload.append({
            "id": result.id,
            "input": result.input,
            "gold": result.gold,
            "answer": result.answer,
            "reason": result.reason or "mismatch",
        })
    return payload


def _answer_ok(task: str, answer) -> bool:
    if not isinstance(answer, ANSWER_TYPES[task]):
        return False
    if task == "train_analysis" and not all(isinstance(item, str) for item in answer):
        return False
    return True


def _parse_answer(text: str, task: str):
    data = parse_json_text(text)
    if not isinstance(data, dict) or not isinstance(data.get("reasoning"), str) or "answer" not in data:
        return None
    if not _answer_ok(task, data["answer"]):
        return None
    return data["answer"]


def _judge(row, answer, score_one) -> ItemResult:
    try:
        passed = bool(score_one(answer, row["gold"]))
    except Exception:
        return ItemResult(row["id"], row["input"], row["gold"], answer, False, "metric_error")
    return ItemResult(row["id"], row["input"], row["gold"], answer, passed, "" if passed else "mismatch")


def _majority(answers: list):
    counts = {}
    first = {}
    best_key = None
    best_count = 0
    keys = []
    for index, answer in enumerate(answers):
        key = canonical_json(answer)
        keys.append(key)
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, index)
        if counts[key] > best_count or (counts[key] == best_count and first[key] < first[best_key]):
            best_count = counts[key]
            best_key = key
    for answer, key in zip(answers, keys):
        if key == best_key:
            return answer
    return None


def _react(messages, client, temperature, task, row, steps):
    transcript = list(messages)
    for _ in range(steps):
        raw = client.complete(transcript, temperature)
        data = parse_json_text(raw)
        if not isinstance(data, dict) or not isinstance(data.get("thought"), str) or not isinstance(data.get("action"), str) or "action_input" not in data:
            return None, "parse_error"
        transcript.append({"role": "assistant", "content": raw})
        action = data["action"]
        if action == "finish":
            payload = data["action_input"]
            if not isinstance(payload, dict) or not isinstance(payload.get("reasoning"), str) or "answer" not in payload:
                return None, "parse_error"
            if not _answer_ok(task, payload["answer"]):
                return None, "parse_error"
            return payload["answer"], ""
        if action == "echo_context":
            observation = "观察：" + canonical_json(row["input"])
        else:
            observation = "观察：unknown action"
        transcript.append({"role": "user", "content": observation})
    return None, "react_unfinished"


def run_validation(slots, method, task, task_brief, val, score_one, client, temperature, self_consistency_n, react_max_steps):
    results = []
    for row in val:
        messages = render_message(slots, method, task, row["input"], task_brief)
        if method == "react":
            answer, reason = _react(messages, client, temperature, task, row, react_max_steps)
            if reason:
                results.append(ItemResult(row["id"], row["input"], row["gold"], answer, False, reason))
            else:
                results.append(_judge(row, answer, score_one))
            continue
        samples = self_consistency_n if method == "self_consistency" else 1
        parsed = []
        for _ in range(samples):
            answer = _parse_answer(client.complete(messages, temperature), task)
            if answer is not None:
                parsed.append(answer)
        if not parsed:
            results.append(ItemResult(row["id"], row["input"], row["gold"], None, False, "parse_error"))
            continue
        chosen = _majority(parsed) if method == "self_consistency" else parsed[0]
        results.append(_judge(row, chosen, score_one))
    return results
