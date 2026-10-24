"""Live demonstration: judge ONE requirement with both judges and print every step.

  python scripts/demo.py                                   # task 39, requirement 5 (original workspace)
  python scripts/demo.py --task <task_name> --req 2 --split generated
"""
import argparse
import textwrap

import _bootstrap  # noqa: F401
from aaj.config import load_config
from aaj.data import ORIGINAL_TASK, build_items
from aaj.judges import JUDGES
from aaj.llm import OllamaChat

ap = argparse.ArgumentParser()
ap.add_argument("--task", default=ORIGINAL_TASK)
ap.add_argument("--req", type=int, default=5)
ap.add_argument("--split", default="original", choices=["original", "generated"])
ap.add_argument("--k", type=int, default=3)
args = ap.parse_args()

cfg = load_config()
j = cfg["judge"]
llm = OllamaChat(cfg["ollama"]["host"], j["model"], temperature=j["temperature"], top_p=j["top_p"],
                 num_ctx=j["num_ctx"], num_predict=j["num_predict"], tokenizer_hf_id=j["tokenizer_hf_id"])
item = next(i for i in build_items(cfg, args.split) if i["task"] == args.task and i["req_id"] == args.req)
print(f"TASK {item['task']}  R{item['req_id']}\nCRITERIA: {item['criteria']}\nHUMAN LABEL: {'SATISFIED' if item['label'] else 'UNSATISFIED'}\n")
for name in ("llm_judge", "agent_judge"):
    print("=" * 70, f"\n{name}")
    res = JUDGES[name](llm, j).judge(item, [11000 + i for i in range(args.k)])
    tok = 0
    for s in res["steps"]:
        if s["step"] == "locate":
            print(f"  locate -> {s['paths']}")
        elif s["step"] == "read":
            print(f"  read   -> opened {s['resolved']}  missing {s['unresolved']}")
        else:
            v = {True: "SATISFIED", False: "UNSATISFIED", None: "UNPARSED"}[s["verdict"]]
            print(f"  judge (seed {s['seed']}) -> {v}: " + textwrap.shorten(s["text"], 160))
        tok += s.get("prompt_tokens", 0) + s.get("completion_tokens", 0)
    votes = [s["verdict"] for s in res["steps"] if s["step"] == "judge"]
    final = sum(bool(v) for v in votes) > len(votes) / 2
    print(f"  MAJORITY of {len(votes)}: {'SATISFIED' if final else 'UNSATISFIED'}   tokens used: {tok}")
