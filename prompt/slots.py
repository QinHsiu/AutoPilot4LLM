import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    input: str
    output: str


@dataclass(frozen=True)
class FiveSlots:
    role: str
    task: str
    context: str
    constraints: str
    output_format: str
    examples: list[Example]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def slots_to_dict(slots: FiveSlots) -> dict:
    return {
        "role": slots.role,
        "task": slots.task,
        "context": slots.context,
        "constraints": slots.constraints,
        "output_format": slots.output_format,
        "examples": [{"input": item.input, "output": item.output} for item in slots.examples],
    }


def slots_from_dict(data: dict) -> FiveSlots:
    examples = [Example(input=item["input"], output=item["output"]) for item in data.get("examples", [])]
    return FiveSlots(
        role=data["role"],
        task=data["task"],
        context=data["context"],
        constraints=data["constraints"],
        output_format=data["output_format"],
        examples=examples,
    )


def working_copy(slots: FiveSlots, method: str) -> FiveSlots:
    examples = list(slots.examples) if method == "few_shot" else []
    return FiveSlots(slots.role, slots.task, slots.context, slots.constraints, slots.output_format, examples)
