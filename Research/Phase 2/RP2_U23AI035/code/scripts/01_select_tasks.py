"""Choose the fixed task subset (stored in data/task_subset.json, committed with the code).

Tasks needing Kaggle credentials or web navigation are excluded because the sandboxed
developer agent has neither. Task 39 is excluded here because it is judged on the
original OpenHands workspace instead.
"""
import json
import random

import _bootstrap  # noqa: F401
from aaj.config import DATA, load_config
from aaj.data import ORIGINAL_TASK, all_task_names, load_instance

cfg = load_config()
sc = cfg["task_subset"]
eligible = []
for t in all_task_names(cfg):
    inst = load_instance(cfg, t)
    if t == ORIGINAL_TASK:
        continue
    if sc["exclude_kaggle"] and inst.get("is_kaggle_api_needed"):
        continue
    if sc["exclude_web_navigation"] and inst.get("is_web_navigation_needed"):
        continue
    eligible.append(t)
rng = random.Random(sc["selection_seed"])
chosen = sorted(set(sc["always_include"]) | set(rng.sample(eligible, min(sc["n_tasks"], len(eligible)))))
n_req = sum(len(load_instance(cfg, t)["requirements"]) for t in chosen)
DATA.mkdir(exist_ok=True)
(DATA / "task_subset.json").write_text(json.dumps(
    {"selection_seed": sc["selection_seed"], "eligible": len(eligible), "tasks": chosen,
     "n_requirements": n_req}, indent=2), encoding="utf-8")
print(f"{len(eligible)} eligible tasks; chose {len(chosen)} with {n_req} requirements -> data/task_subset.json")
