import json
from dataclasses import dataclass

from prompt.slots import canonical_json


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reason: str


ALLOWED = {"role", "task", "context", "constraints", "output_format", "examples"}


def strip_fence(text: str) -> str:
    stripped = text.strip()
    prefix = "```json"
    if stripped.startswith(prefix) and stripped.endswith("```"):
        return stripped[len(prefix):-3].strip()
    return text


def parse_json_text(text: str):
    try:
        return json.loads(strip_fence(text))
    except json.JSONDecodeError:
        return None


def constraint_sentences(text: str) -> list[str]:
    sentences = []
    for line in text.split("\n"):
        for piece in line.split("。"):
            stripped = piece.strip()
            if stripped:
                sentences.append(stripped)
    return sentences


def check_gate(payload: dict, method: str, task: str, val_inputs: list) -> GateResult:
    if not isinstance(payload, dict):
        return GateResult(False, "parse_error")
    if "method" in payload:
        return GateResult(False, "method_key")
    extra = sorted(set(payload) - ALLOWED)
    if extra:
        return GateResult(False, "extra_key:" + extra[0])
    for field in ("role", "task", "context", "constraints", "output_format"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return GateResult(False, f"empty_field:{field}")
    reasoning_at = payload["output_format"].find("reasoning")
    answer_at = payload["output_format"].find("answer")
    if reasoning_at < 0 or answer_at < 0 or reasoning_at > answer_at:
        return GateResult(False, "output_format")
    for sentence in constraint_sentences(payload["constraints"]):
        if sentence.startswith(("不要", "禁止", "勿")) or (sentence.startswith("别") and not sentence.startswith("别的")):
            return GateResult(False, "constraint:" + sentence)
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        return GateResult(False, "example_count")
    if method == "few_shot":
        if not 2 <= len(examples) <= 5:
            return GateResult(False, "example_count")
        canonical_inputs = {canonical_json(item) for item in val_inputs}
        for example in examples:
            if not isinstance(example, dict):
                return GateResult(False, "example_empty")
            raw_input = example.get("input")
            raw_output = example.get("output")
            if not isinstance(raw_input, str) or not isinstance(raw_output, str):
                return GateResult(False, "example_empty")
            if not raw_input.strip() or not raw_output.strip():
                return GateResult(False, "example_empty")
            try:
                example_key = canonical_json(json.loads(raw_input))
            except json.JSONDecodeError:
                example_key = raw_input
            if example_key in canonical_inputs:
                return GateResult(False, "example_overlaps_val")
    elif examples:
        return GateResult(False, "examples_must_be_empty")
    if "{item}" not in payload["context"]:
        return GateResult(False, "missing_placeholder:{item}")
    if task == "distill" and "{task_brief}" not in payload["context"]:
        return GateResult(False, "missing_placeholder:{task_brief}")
    return GateResult(True, "")
