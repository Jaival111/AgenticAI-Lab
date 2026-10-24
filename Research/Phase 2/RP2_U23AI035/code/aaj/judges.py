"""The two judges compared in this project. They share the same judging prompt and model;
they differ in ONE thing only: how the evidence shown to that prompt is gathered.

  LLMJudge   (baseline)  evidence = whole-workspace dump; k samples, majority vote
  AgentJudge (method)    evidence = workspace tree + files chosen by an LLM `locate` step
                         and opened by `read`; k samples of the final verdict, majority vote

Both draw k_max samples per requirement and store every sample, so majority voting for
any k <= k_max is computed offline (aaj.metrics). This lets one run trace the whole
accuracy-versus-tokens curve and pick the budget-matched k afterwards.
"""
from __future__ import annotations

import re
from pathlib import Path

from aaj.config import load_prompt
from aaj.llm import OllamaChat
from aaj.workspace import dump_workspace, read_file, render_tree, resolve_workspace_path

VERDICT_RE = re.compile(r"<\s*(UN)?SATISFIED\s*>", re.IGNORECASE)
PATH_RE = re.compile(r"\$([^$\n]+)\$")


def parse_verdict(text: str) -> bool | None:
    """True / False from the first verdict tag; None when the model gave no tag."""
    m = VERDICT_RE.search(text or "")
    if not m:
        return None
    return m.group(1) is None


def parse_paths(text: str, limit: int) -> list[str]:
    seen = []
    for p in PATH_RE.findall(text or ""):
        p = p.strip()
        if p and p not in seen:
            seen.append(p)
    return seen[:limit]


class _Base:
    name = "base"

    def __init__(self, llm: OllamaChat, jcfg: dict):
        self.llm = llm
        self.cfg = jcfg
        self.hf = jcfg.get("tokenizer_hf_id")
        self.sys_judge = load_prompt("judge_system")
        self.user_judge = load_prompt("judge_user")

    def _verdict_samples(self, evidence: str, criteria: str, seeds: list[int]) -> list[dict]:
        messages = [{"role": "system", "content": self.sys_judge},
                    {"role": "user", "content": self.user_judge.format(evidence=evidence, criteria=criteria)}]
        samples = []
        for s in seeds:
            res = self.llm.chat(messages, seed=s)
            samples.append({"step": "judge", "verdict": parse_verdict(res.text), **res.to_dict(),
                            "messages": messages if s == seeds[0] else "[same as first sample]"})
        return samples


class LLMJudge(_Base):
    """LLM-as-a-Judge baseline: the workspace is "directly input" to the model, as the
    DevAI authors describe for their baseline (GitHub issue #20)."""
    name = "llm_judge"

    def judge(self, item: dict, seeds: list[int]) -> dict:
        root = Path(item["workspace"])
        evidence = dump_workspace(root, self.cfg["max_dump_tokens"], self.hf,
                                  self.cfg["max_tree_lines"], self.cfg["max_file_tokens"])
        steps = self._verdict_samples(evidence, item["criteria"], seeds)
        return {"judge": self.name, "steps": steps, "evidence_chars": len(evidence)}


class AgentJudge(_Base):
    """Agent-as-a-Judge, black-box, with the module set the paper found best for OpenHands
    without trajectories: graph (here: the tree) -> locate -> read -> ask."""
    name = "agent_judge"

    def __init__(self, llm: OllamaChat, jcfg: dict):
        super().__init__(llm, jcfg)
        self.sys_locate = load_prompt("locate_system")
        self.user_locate = load_prompt("locate_user")

    def judge(self, item: dict, seeds: list[int]) -> dict:
        root = Path(item["workspace"])
        tree = render_tree(root, self.cfg["max_tree_lines"])
        # 1) locate: one call, seeded with the run's first seed
        loc_msgs = [{"role": "system", "content": self.sys_locate},
                    {"role": "user", "content": self.user_locate.format(workspace_info=tree, criteria=item["criteria"])}]
        loc = self.llm.chat(loc_msgs, seed=seeds[0])
        paths = parse_paths(loc.text, self.cfg["max_locate_files"])
        steps = [{"step": "locate", "paths": paths, **loc.to_dict(), "messages": loc_msgs}]
        # 2) read: no model call, open the located files
        evidence = f">>> [Key Evidence] Workspace Structure:\n\n{tree}\n\n"
        evidence += f">>> [Reference] Located Files:\n\n{paths}\n\n"
        unresolved = []
        for p in paths:
            real = resolve_workspace_path(root, p)
            if real is None:
                unresolved.append(p)
                continue
            content = read_file(real, self.cfg["max_file_tokens"], self.hf)
            evidence += f">>> [Key Evidence] Content of Files:\n\nContent of {p}:\n```\n{content}\n```\n"
        if not paths or len(unresolved) == len(paths):
            evidence += ">>> [Reference] None of the located files exist in the workspace.\n"
        steps.append({"step": "read", "resolved": [p for p in paths if p not in unresolved],
                      "unresolved": unresolved})
        # 3) ask: k samples of the verdict on the gathered evidence
        steps += self._verdict_samples(evidence, item["criteria"], seeds)
        return {"judge": self.name, "steps": steps, "evidence_chars": len(evidence)}


class AgentNoReadJudge(AgentJudge):
    """Ablation: the agent judge with the `read` module removed. It still locates files but
    sees only the tree and the located paths, never their contents."""
    name = "agent_noread"

    def judge(self, item: dict, seeds: list[int]) -> dict:
        root = Path(item["workspace"])
        tree = render_tree(root, self.cfg["max_tree_lines"])
        loc_msgs = [{"role": "system", "content": self.sys_locate},
                    {"role": "user", "content": self.user_locate.format(workspace_info=tree, criteria=item["criteria"])}]
        loc = self.llm.chat(loc_msgs, seed=seeds[0])
        paths = parse_paths(loc.text, self.cfg["max_locate_files"])
        existing = [p for p in paths if resolve_workspace_path(root, p) is not None]
        evidence = (f">>> [Key Evidence] Workspace Structure:\n\n{tree}\n\n"
                    f">>> [Reference] Located Files (existing): {existing}\n\n")
        steps = [{"step": "locate", "paths": paths, **loc.to_dict(), "messages": loc_msgs}]
        steps += self._verdict_samples(evidence, item["criteria"], seeds)
        return {"judge": self.name, "steps": steps, "evidence_chars": len(evidence)}


JUDGES = {"llm_judge": LLMJudge, "agent_judge": AgentJudge, "agent_noread": AgentNoReadJudge}
