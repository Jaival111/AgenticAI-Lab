"""Interactive labelling of every requirement of every generated workspace (the ground truth).

  python scripts/03_label.py --labeler "U23AI035"

Label BEFORE running any judge (the script refuses if judge results already exist, unless
--allow-after-judging is given) so that the labels cannot be influenced by judge outputs.
Rules (from the DevAI paper, Appendix H, evaluator 38bb; written down here so they are applied
consistently): judge each requirement on its own, ignoring prerequisites; a file must exist
at the requested path with meaningful content; code that obviously cannot work is UNSATISFIED;
you may read code but you do not need to run it.

Commands at the prompt:  y = satisfied   n = unsatisfied   o = open a file   t = show tree
                         q = save and quit (progress is kept; rerun to continue)
Output: data/labels/<developer>/<task>.json in the DevAI human_as_a_judge format, plus the
labeller, the time spent per requirement and a UTC timestamp.
"""
import argparse
import datetime as dt
import json
import time
from pathlib import Path

import _bootstrap  # noqa: F401
from aaj.config import RESULTS, load_config
from aaj.data import generated_workspace, label_path, load_instance, load_subset
from aaj.workspace import iter_files, read_file, render_tree, to_workspace_path

ap = argparse.ArgumentParser()
ap.add_argument("--labeler", required=True)
ap.add_argument("--allow-after-judging", action="store_true")
args = ap.parse_args()

cfg = load_config()
if RESULTS.exists() and any(RESULTS.glob("*/*/seed_*.jsonl")) and not args.allow_after_judging:
    raise SystemExit("Judge results already exist. Labels must be written blind; pass --allow-after-judging only if you document it.")


def open_file(root: Path):
    files = list(iter_files(root))
    for i, f in enumerate(files):
        print(f"  [{i}] {to_workspace_path(root, f)}")
    choice = input("  file number (blank = back): ").strip()
    if choice.isdigit() and int(choice) < len(files):
        print("-" * 70)
        print(read_file(files[int(choice)], max_tokens=6000, hf_id=None))
        print("-" * 70)


for task in load_subset(cfg):
    lp = label_path(cfg, task)
    lab = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else load_instance(cfg, task)
    reqs = lab["requirements"]
    if all(r.get("satisfied") is not None for r in reqs):
        continue
    root = generated_workspace(cfg, task)
    print("=" * 78)
    print(f"TASK {task}\n\n{lab['query']}\n")
    print(render_tree(root))
    for r in reqs:
        if r.get("satisfied") is not None:
            continue
        print(f"\nR{r['requirement_id']} [{r.get('category', '')}]: {r['criteria']}")
        t0 = time.perf_counter()
        while True:
            a = input("  y / n / o(pen) / t(ree) / q(uit) > ").strip().lower()
            if a == "o":
                open_file(root)
            elif a == "t":
                print(render_tree(root))
            elif a in ("y", "n"):
                r["satisfied"] = a == "y"
                r["label_seconds"] = round(time.perf_counter() - t0, 1)
                break
            elif a == "q":
                break
        if a == "q":
            break
        lab.update(labeler=args.labeler, labelled_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(lab, indent=2), encoding="utf-8")  # save after every answer
    if a == "q":
        print("saved; rerun to continue")
        break
else:
    print("all requirements labelled")
