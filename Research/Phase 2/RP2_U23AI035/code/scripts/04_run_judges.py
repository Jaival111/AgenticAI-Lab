"""Run one judge over the evaluation items, once per seed, saving results and full traces.

  python scripts/04_run_judges.py --judge llm_judge
  python scripts/04_run_judges.py --judge agent_judge
  python scripts/04_run_judges.py --judge agent_noread --k 1        # ablation
  python scripts/04_run_judges.py --judge agent_judge --split original --limit 3   # smoke test

Outputs
  results/<run_id>/manifest.json                    pinned config + model digest + dates
  results/<run_id>/<judge>/seed_<s>.jsonl           one record per requirement (no prompts)
  traces/<run_id>/<judge>/seed_<s>/<task>__R<i>.json full trace: every prompt, output, cost
Already-finished requirements are skipped, so an interrupted run can simply be restarted.
"""
import argparse
import datetime as dt
import json
import platform
import sys
import time

import _bootstrap  # noqa: F401
from aaj.config import RESULTS, TRACES, load_config
from aaj.data import build_items
from aaj.judges import JUDGES
from aaj.llm import LLMError, OllamaChat
from aaj.tokens import tokenizer_status

ap = argparse.ArgumentParser()
ap.add_argument("--judge", required=True, choices=sorted(JUDGES))
ap.add_argument("--split", default="all", choices=["all", "original", "generated"])
ap.add_argument("--run-id", default="main")
ap.add_argument("--seeds", type=int, nargs="*", help="override the seeds in the config")
ap.add_argument("--k", type=int, help="samples per requirement (default: k_max from config)")
ap.add_argument("--limit", type=int, help="only the first N items (smoke test)")
args = ap.parse_args()

cfg = load_config()
j = cfg["judge"]
k = args.k or j["k_max"]
seeds = args.seeds or j["seeds"]
llm = OllamaChat(cfg["ollama"]["host"], j["model"], temperature=j["temperature"], top_p=j["top_p"],
                 num_ctx=j["num_ctx"], num_predict=j["num_predict"], timeout_s=cfg["ollama"]["request_timeout_s"],
                 max_retries=cfg["ollama"]["max_retries"], tokenizer_hf_id=j["tokenizer_hf_id"])
judge = JUDGES[args.judge](llm, j)
items = build_items(cfg, args.split)[: args.limit]
print(f"{args.judge}: {len(items)} requirements x {len(seeds)} seeds x k={k}")

run_dir = RESULTS / args.run_id
run_dir.mkdir(parents=True, exist_ok=True)
manifest_path = run_dir / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"judges": {}}
manifest.update(config=cfg, judge_model_info=llm.model_info(), python=sys.version, platform=platform.platform())
manifest["judges"][args.judge] = {"k": k, "seeds": seeds, "split": args.split, "n_items": len(items),
                                  "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}

for seed in seeds:
    out = run_dir / args.judge / f"seed_{seed}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if not rec.get("error"):
                done.add((rec["task"], rec["req_id"]))
    sample_seeds = [seed * 1000 + i for i in range(k)]
    t_seed = time.perf_counter()
    for n, it in enumerate(items, 1):
        if (it["task"], it["req_id"]) in done:
            continue
        rec = {key: it[key] for key in ("split", "task", "req_id", "criteria", "category", "label")}
        rec.update(judge=args.judge, seed=seed, k=k)
        try:
            res = judge.judge(it, sample_seeds)
            rec["steps"] = [{x: v for x, v in s.items() if x != "messages"} for s in res["steps"]]
            rec["evidence_chars"] = res["evidence_chars"]
            trace = dict(rec, steps=res["steps"], workspace=it["workspace"])
        except (LLMError, OSError) as e:  # recorded, excluded from scoring, retried on restart
            rec["steps"], rec["error"] = [], repr(e)
            trace = dict(rec)
            print(f"  !! {it['task']} R{it['req_id']}: {e}")
        tp = TRACES / args.run_id / args.judge / f"seed_{seed}" / f"{it['task']}__R{it['req_id']}.json"
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if n % 10 == 0:
            print(f"  seed {seed}: {n}/{len(items)}  ({time.perf_counter() - t_seed:.0f} s)")
    print(f"seed {seed} finished in {time.perf_counter() - t_seed:.0f} s -> {out}")

manifest["judges"][args.judge]["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
manifest["tokenizer"] = tokenizer_status()
manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
