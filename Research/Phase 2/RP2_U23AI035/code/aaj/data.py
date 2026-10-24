"""DevAI tasks, workspaces and ground-truth labels.

Two evaluation sets are built:
  * "original"  : task 39, the only OpenHands workspace the DevAI authors released, judged
                  against the authors' human-consensus labels (published-label check).
  * "generated" : workspaces produced by our local developer agent on the task subset,
                  judged against labels written by the student with scripts/03_label.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from aaj.config import DATA, devai_dir

ORIGINAL_TASK = "39_Drug_Response_Prediction_SVM_GDSC_ML"


def slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def instances_dir(cfg) -> Path:
    return devai_dir(cfg) / "benchmark" / "devai" / "instances"


def load_instance(cfg, task: str) -> dict:
    return json.loads((instances_dir(cfg) / f"{task}.json").read_text(encoding="utf-8"))


def all_task_names(cfg) -> list[str]:
    return sorted(p.stem for p in instances_dir(cfg).glob("*.json"))


def generated_workspace(cfg, task: str) -> Path:
    return DATA / "workspaces" / slug(cfg["developer"]["model"]) / task


def generated_trajectory(cfg, task: str) -> Path:
    return DATA / "trajectories" / slug(cfg["developer"]["model"]) / f"{task}.json"


def original_workspace(cfg, task: str = ORIGINAL_TASK) -> Path:
    return devai_dir(cfg) / "benchmark" / "workspaces" / "OpenHands" / task


def original_labels(cfg, task: str = ORIGINAL_TASK) -> dict:
    p = devai_dir(cfg) / "benchmark" / "judgment" / "OpenHands" / "human_as_a_judge" / f"{task}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def label_path(cfg, task: str) -> Path:
    return DATA / "labels" / slug(cfg["developer"]["model"]) / f"{task}.json"


def load_subset(cfg) -> list[str]:
    p = DATA / "task_subset.json"
    if not p.exists():
        raise FileNotFoundError("data/task_subset.json missing - run scripts/01_select_tasks.py first")
    return json.loads(p.read_text(encoding="utf-8"))["tasks"]


def build_items(cfg, which: str) -> list[dict]:
    """One item per (task, requirement) with its ground-truth label and workspace path."""
    items = []
    if which in ("original", "all"):
        lab = original_labels(cfg)
        for r in lab["requirements"]:
            items.append(_item("original", ORIGINAL_TASK, r, original_workspace(cfg), lab["query"]))
    if which in ("generated", "all"):
        missing = []
        for task in load_subset(cfg):
            lp = label_path(cfg, task)
            if not lp.exists():
                missing.append(task)
                continue
            lab = json.loads(lp.read_text(encoding="utf-8"))
            for r in lab["requirements"]:
                if r.get("satisfied") is None:
                    raise ValueError(f"{lp} has an unlabelled requirement {r['requirement_id']}")
                items.append(_item("generated", task, r, generated_workspace(cfg, task), lab["query"]))
        if missing:
            print(f"[warn] {len(missing)} tasks have no labels yet and are skipped: {missing}")
    return items


def _item(split, task, req, workspace: Path, query: str) -> dict:
    return {"split": split, "task": task, "req_id": req["requirement_id"],
            "criteria": req["criteria"], "category": req.get("category", ""),
            "prerequisites": req.get("prerequisites", []), "label": bool(req["satisfied"]),
            "workspace": str(workspace), "query": query}
