import os
from dataclasses import dataclass
from datetime import datetime

from prompt.config import config_public
from prompt.errors import PreflightError
from prompt.gate import check_gate, parse_json_text
from prompt.llm import LlmError, OpenAiCompatibleClient
from prompt.methods import render_body
from prompt.runner import failure_payload, run_validation
from prompt.slots import FiveSlots, canonical_json, slots_from_dict, slots_to_dict, working_copy
from prompt.store import append_version, make_run_dir, write_run
from prompt.tasks.load import load_pack

METHODS = {"zero_shot", "few_shot", "cot", "self_consistency", "react"}
META_ROLE = "你是一名只改写提示词五格的修订员，只根据失败样本调整职责、任务、上下文、约束和输出格式。"
META_TASK = "给出一份新的五格，使同一方法在同一验证集上通过更多样本。"
META_CONTEXT = "方法名是 {method}。当前五格是 {slots}。失败样本是 {failures}。"
META_CONSTRAINTS = "保持方法不变，不在 JSON 中写入方法名。保留上下文里原有的占位符。Few-Shot 时示例数量保持 2 到 5 条，其他方法的示例必须是空数组。约束用肯定句。输出格式中 reasoning 写在 answer 之前。"
META_OUTPUT = "只输出一个 JSON 对象，键顺序为 role、task、context、constraints、output_format、examples。reasoning 不出现在这个 JSON 里。"


def replace_once(template: str, mapping: dict[str, str]) -> str:
    keys = sorted(mapping, key=len, reverse=True)
    pieces = []
    index = 0
    while index < len(template):
        matched = False
        for key in keys:
            token = "{" + key + "}"
            if template.startswith(token, index):
                pieces.append(mapping[key])
                index += len(token)
                matched = True
                break
        if not matched:
            pieces.append(template[index])
            index += 1
    return "".join(pieces)


def evolver_messages(method: str, slots: FiveSlots, failures: list[dict]) -> list[dict]:
    context = replace_once(META_CONTEXT, {
        "method": method,
        "slots": canonical_json(slots_to_dict(slots)),
        "failures": canonical_json(failures),
    })
    meta = FiveSlots(META_ROLE, META_TASK, context, META_CONSTRAINTS, META_OUTPUT, [])
    return [{"role": "user", "content": render_body(meta, "zero_shot")}]


@dataclass
class EvolveResult:
    best_slots: FiveSlots | None
    best_passed: int | None
    best_score: float | None
    stop_reason: str
    run_dir: str | None


def exit_code(result: EvolveResult) -> int:
    return 1 if result.stop_reason == "seed_score_failed" else 0


def _count(results) -> int:
    return sum(1 for result in results if result.passed)


def evolve(task, method, config, task_brief=None, val_path=None, client=None, clock=None, runs_root=None) -> EvolveResult:
    if method not in METHODS:
        raise PreflightError(f"unknown method: {method}")
    if task_brief is not None and task != "distill":
        raise PreflightError("task_brief is only valid for distill")
    if task == "distill" and task_brief is not None and not val_path:
        raise PreflightError("task_brief requires val_path")
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise PreflightError(f"missing env: {config.api_key_env}")
    pack = load_pack(task, val_path)
    brief = task_brief if task == "distill" and task_brief is not None else pack.task_brief
    current = working_copy(pack.slots, method)
    gate = check_gate(slots_to_dict(current), method, task, [row["input"] for row in pack.val])
    if not gate.ok:
        raise PreflightError("seed failed gate: " + gate.reason)
    if client is None:
        client = OpenAiCompatibleClient(config, api_key)
    run_dir = make_run_dir(runs_root or "runs", task, method, (clock or datetime.now)())
    total = len(pack.val)
    accepted_version = None
    counter = 0

    def log(kind, slots, accepted, passed, failures):
        nonlocal counter, accepted_version
        record = {
            "version": counter,
            "parent": accepted_version,
            "method": method,
            "slots": slots_to_dict(slots),
            "passed": passed,
            "total": total,
            "score": None if passed is None else passed / total,
            "accepted": accepted,
            "failures": failures,
            "kind": kind,
        }
        append_version(run_dir, record)
        if accepted:
            accepted_version = counter
        counter += 1

    def finish(reason, slots, passed):
        write_run(run_dir, {
            "task": task,
            "method": method,
            "stop_reason": reason,
            "best_version": accepted_version,
            "best_passed": passed,
            "best_score": None if passed is None else passed / total,
            "config": config_public(config),
        })
        return EvolveResult(slots, passed, None if passed is None else passed / total, reason, str(run_dir))

    try:
        results = run_validation(
            current, method, task, brief, pack.val, pack.score_one, client,
            config.temperature, config.self_consistency_n, config.react_max_steps,
        )
    except LlmError:
        log("llm_error", current, False, None, [{"reason": "llm_error"}])
        return finish("seed_score_failed", None, None)
    passed = _count(results)
    log("seed", current, True, passed, failure_payload(results))
    if passed == total:
        return finish("perfect_score", current, passed)
    for _ in range(config.max_iters):
        try:
            raw = client.complete(
                evolver_messages(method, current, failure_payload(results)),
                config.evolver_temperature,
            )
        except LlmError:
            log("llm_error", current, False, None, [{"reason": "llm_error"}])
            return finish("llm_error", current, passed)
        payload = parse_json_text(raw)
        if not isinstance(payload, dict):
            log("gate_reject", current, False, None, [{"reason": "parse_error"}])
            continue
        decision = check_gate(payload, method, task, [row["input"] for row in pack.val])
        if not decision.ok:
            log("gate_reject", current, False, None, [{"reason": decision.reason}])
            continue
        candidate = slots_from_dict(payload)
        try:
            candidate_results = run_validation(
                candidate, method, task, brief, pack.val, pack.score_one, client,
                config.temperature, config.self_consistency_n, config.react_max_steps,
            )
        except LlmError:
            log("llm_error", candidate, False, None, [{"reason": "llm_error"}])
            return finish("llm_error", current, passed)
        new_passed = _count(candidate_results)
        if new_passed <= passed:
            log("candidate", candidate, False, new_passed, failure_payload(candidate_results))
            return finish("no_improvement", current, passed)
        current = candidate
        results = candidate_results
        passed = new_passed
        log("candidate", current, True, passed, failure_payload(results))
        if passed == total:
            return finish("perfect_score", current, passed)
    return finish("max_iters", current, passed)
