"""A minimal developer agent that produces DevAI workspaces to be judged.

Why it exists: the DevAI authors released the OpenHands workspace of only one task
(GitHub issue #36), so the outputs their human labels refer to are not available.
We therefore generate our own workspaces with a local model and label them ourselves.

The agent is a write/run/finish loop with a 30-minute limit, as in the paper (Sec. 2.3).
It records a trajectory in the DevAI trajectory schema (one entry per step).

SAFETY: `run` actions execute model-written shell commands. They are refused unless
`allow_exec=True`, which the CLI only sets inside the Docker sandbox (docker/Dockerfile.devagent)
or when the user passes --i-understand-exec-risk.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from aaj.config import load_prompt
from aaj.llm import OllamaChat

ACTION_RE = re.compile(r"```(write|run|finish)([^\n]*)\n(.*?)```", re.DOTALL)
MAX_OBS_CHARS = 3000


def parse_action(text: str) -> tuple[str, str, str] | None:
    m = ACTION_RE.search(text or "")
    if not m:
        return None
    kind, header, body = m.group(1), m.group(2).strip(), m.group(3)
    return kind, header, body


def _safe_path(root: Path, header: str) -> Path | None:
    m = re.search(r"path\s*=\s*(\S+)", header)
    if not m:
        return None
    rel = m.group(1).strip("`'\"").lstrip("/").replace("\\", "/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p


def build_constraints(instance: dict, constraints: dict) -> str:
    parts = [constraints["generic"]]
    if instance.get("is_training_needed"):
        parts.append(constraints["is_training_needed"])
    return "\n\n".join(parts)


def run_developer(instance: dict, constraints: dict, workspace: Path, llm: OllamaChat, dcfg: dict,
                  allow_exec: bool, log=print) -> list[dict]:
    workspace.mkdir(parents=True, exist_ok=True)
    messages = [{"role": "system", "content": load_prompt("dev_system")},
                {"role": "user", "content": load_prompt("dev_user").format(
                    query=instance["query"], constraints=build_constraints(instance, constraints))}]
    trajectory, t_start, acc_cost = [], time.perf_counter(), 0.0
    for step in range(dcfg["max_steps"]):
        elapsed = time.perf_counter() - t_start
        if elapsed > dcfg["time_limit_s"]:
            log(f"  time limit reached after {step} steps")
            break
        t_step = time.perf_counter()
        res = llm.chat(messages, seed=dcfg["seed"] + step)
        action = parse_action(res.text)
        if action is None:
            obs = "No valid action block found. Reply with exactly one ```write path=...```, ```run``` or ```finish``` block."
            kind = "invalid"
        else:
            kind, header, body = action
            if kind == "write":
                p = _safe_path(workspace, header)
                if p is None:
                    obs = "Refused: the write path is missing or outside the project folder."
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(body, encoding="utf-8")
                    obs = f"Wrote {p.relative_to(workspace).as_posix()} ({len(body)} characters)."
            elif kind == "run":
                obs = _execute(body.strip(), workspace, dcfg, allow_exec,
                               remaining=dcfg["time_limit_s"] - (time.perf_counter() - t_start))
            else:
                obs = "Finished."
        log(f"  step {step:2d} {kind:7s} {obs[:90]!r}")
        messages += [{"role": "assistant", "content": res.text},
                     {"role": "user", "content": f"Result:\n{obs}"}]
        trajectory.append({
            "step": step, "user_message": messages[1]["content"] if step == 0 else None,
            "agent": {"thought": res.text, "action": kind, "agent_name": "aaj-devagent"},
            "environment": obs,
            "step_usage": {"input_tokens": res.prompt_tokens, "output_tokens": res.completion_tokens,
                           "model": res.model, "cost": 0.0, "llm_inference_time": res.latency_s,
                           "step_execution_time": time.perf_counter() - t_step},
            "accumulated_usage": {"accumulated_cost": acc_cost,
                                  "accumulated_time": time.perf_counter() - t_start}})
        if kind == "finish":
            break
        messages = _trim_history(messages)
    return trajectory


def _execute(cmd: str, cwd: Path, dcfg: dict, allow_exec: bool, remaining: float) -> str:
    if not allow_exec:
        return "Command execution is disabled in this environment. Write the files only; they will be inspected without running them."
    timeout = max(5, min(dcfg["exec_timeout_s"], remaining))
    try:
        cp = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                            timeout=timeout, errors="replace")
        out = f"exit code {cp.returncode}\nstdout:\n{cp.stdout[-MAX_OBS_CHARS:]}\nstderr:\n{cp.stderr[-MAX_OBS_CHARS:]}"
    except subprocess.TimeoutExpired:
        out = f"Command timed out after {timeout:.0f} s."
    return out


def _trim_history(messages: list[dict], keep_last: int = 16) -> list[dict]:
    """Keep the system prompt, the task, and the most recent turns so the context does not overflow."""
    if len(messages) <= 2 + keep_last:
        return messages
    return messages[:2] + [{"role": "user", "content": "[earlier steps omitted to save context]"}] + messages[-keep_last:]


def save_trajectory(trajectory: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trajectory, indent=2), encoding="utf-8")
