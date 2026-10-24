"""Regenerate every table, figure and the failure-case list from the saved results.

  python scripts/05_analyze.py [--run-id main]

Writes to results/<run_id>/:
  tables.md               all tables (mean +- std over seeds), pasted into the report
  scores_long.csv         one row per (split, judge, k, seed)
  summary.json            the numbers the report and slides are filled from
  fig1_budget_curve.png   agreement vs tokens per requirement for both judges (k = 1..k_max)
  fig2_by_category.png    alignment by requirement category, k = 1
  failure_cases.md        requirements the agent judge gets wrong in most seeds, with trace paths
"""
import argparse
import csv
import json
from collections import defaultdict

import _bootstrap  # noqa: F401
from aaj.config import RESULTS, TRACES, load_config
from aaj.data import label_path, load_subset
from aaj.metrics import aggregate, alignment, cohen_kappa, matched_k, score_run, vote

ap = argparse.ArgumentParser()
ap.add_argument("--run-id", default="main")
args = ap.parse_args()
cfg = load_config()
run_dir = RESULTS / args.run_id
manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

# ---------- load (keep the last successful record per requirement) ----------
records = defaultdict(dict)   # (judge, seed) -> {(task, req): rec}
errors = defaultdict(int)
for f in sorted(run_dir.glob("*/seed_*.jsonl")):
    judge, seed = f.parent.name, int(f.stem.split("_")[1])
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("error"):
            errors[judge] += 1
            continue
        records[(judge, seed)][(r["task"], r["req_id"])] = r
judges = sorted({j for j, _ in records})
seeds_of = {j: sorted(s for jj, s in records if jj == j) for j in judges}


def recs(judge, seed, split):
    return [r for r in records[(judge, seed)].values() if split == "all" or r["split"] == split]


def fmt(m, s, pct=False, nd=1):
    if pct:
        return f"{100 * m:.{nd}f} ± {100 * s:.{nd}f}"
    return f"{m:.{nd}f} ± {s:.{nd}f}"


# ---------- scores for every (split, judge, k) ----------
rows, agg = [], {}
for split in ("generated", "original"):
    for j in judges:
        k_max = manifest["judges"].get(j, {}).get("k", 1)
        for k in range(1, k_max + 1):
            per_seed = []
            for s in seeds_of[j]:
                rs = recs(j, s, split)
                if rs:
                    sc = score_run(rs, k)
                    per_seed.append(sc)
                    rows.append({"split": split, "judge": j, "k": k, "seed": s, **sc})
            if per_seed:
                agg[(split, j, k)] = aggregate(per_seed)

with open(run_dir / "scores_long.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# ---------- budget matching ----------
S = "generated"
summary = {"run_id": args.run_id, "errors_excluded": dict(errors), "judges": judges,
           "n_requirements": {sp: len(recs(judges[0], seeds_of[judges[0]][0], sp)) for sp in ("generated", "original")},
           "n_tasks": len(load_subset(cfg)), "seeds": seeds_of, "model": manifest["judge_model_info"],
           "config": manifest["config"]["judge"], "tokenizer": manifest.get("tokenizer", {})}
matched = {}
if ("llm_judge" in judges) and ("agent_judge" in judges):
    tok = lambda j: {k: agg[(S, j, k)]["tokens_per_req"] for (sp, jj, k) in agg if sp == S and jj == j}
    a1, b1 = agg[(S, "agent_judge", 1)]["tokens_per_req"], agg[(S, "llm_judge", 1)]["tokens_per_req"]
    kb = matched_k(tok("llm_judge"), a1)   # baseline given the agent's budget
    ka = matched_k(tok("agent_judge"), b1)  # agent given the baseline's budget
    matched = {"agent@1_vs_llm@k": {"k_llm": kb, "agent": agg[(S, "agent_judge", 1)], "llm": agg[(S, "llm_judge", kb)]},
               "llm@1_vs_agent@k": {"k_agent": ka, "llm": agg[(S, "llm_judge", 1)], "agent": agg[(S, "agent_judge", ka)]}}
    summary["matched"] = matched

# ---------- tables ----------
k_eval = cfg["judge"]["k_eval"]
L = [f"# Results ({args.run_id})\n",
     f"Judge model: `{manifest['judge_model_info']['model']}` digest `{manifest['judge_model_info'].get('digest')}`; "
     f"temperature {cfg['judge']['temperature']}, top-p {cfg['judge']['top_p']}, seeds {cfg['judge']['seeds']}; "
     f"mean ± std over {len(seeds_of.get('agent_judge', seeds_of[judges[0]]))} runs. Errors excluded: {dict(errors) or 'none'}.\n"]


def score_table(split, title):
    out = [f"\n## {title}\n", "| Judge | k | Alignment % | Cohen κ | F1 (satisfied) | Calls/req | Tokens/req | Latency s/req | Unparsed % |",
           "|---|---|---|---|---|---|---|---|---|"]
    for j in judges:
        for k in k_eval:
            a = agg.get((split, j, k))
            if not a:
                continue
            out.append(f"| {j} | {k} | {fmt(a['alignment'], a['alignment_std'], True)} | {fmt(a['kappa'], a['kappa_std'], nd=3)} | "
                       f"{fmt(a['f1_pos'], a['f1_pos_std'], nd=3)} | {a['calls_per_req']:.1f} | {fmt(a['tokens_per_req'], a['tokens_per_req_std'], nd=0)} | "
                       f"{fmt(a['latency_s_per_req'], a['latency_s_per_req_std'])} | {100 * a['unparsed']:.1f} |")
    return out


L += score_table("generated", "Table 1. Main results on generated workspaces (student labels)")
if matched:
    m1, m2 = matched["agent@1_vs_llm@k"], matched["llm@1_vs_agent@k"]
    L += ["\n## Table 2. Matched-budget comparisons (generated split)\n",
          "| Comparison | Agent alignment % | LLM alignment % | Agent κ | LLM κ | Agent tokens/req | LLM tokens/req |", "|---|---|---|---|---|---|---|",
          f"| agent@1 vs llm@{m1['k_llm']} | {fmt(m1['agent']['alignment'], m1['agent']['alignment_std'], True)} | {fmt(m1['llm']['alignment'], m1['llm']['alignment_std'], True)} | "
          f"{m1['agent']['kappa']:.3f} | {m1['llm']['kappa']:.3f} | {m1['agent']['tokens_per_req']:.0f} | {m1['llm']['tokens_per_req']:.0f} |",
          f"| agent@{m2['k_agent']} vs llm@1 | {fmt(m2['agent']['alignment'], m2['agent']['alignment_std'], True)} | {fmt(m2['llm']['alignment'], m2['llm']['alignment_std'], True)} | "
          f"{m2['agent']['kappa']:.3f} | {m2['llm']['kappa']:.3f} | {m2['agent']['tokens_per_req']:.0f} | {m2['llm']['tokens_per_req']:.0f} |"]
abl = [j for j in ("llm_judge", "agent_noread", "agent_judge") if (S, j, 1) in agg]
if len(abl) > 1:
    L += ["\n## Table 3. Ablation of the evidence-gathering component (k = 1, generated split)\n",
          "| Evidence given to the same prompt | Alignment % | Cohen κ | Tokens/req |", "|---|---|---|---|"]
    names = {"llm_judge": "whole-workspace dump (= ablation: locate + read removed)",
             "agent_noread": "tree + located paths (read removed)", "agent_judge": "tree + located files read (full agent)"}
    for j in abl:
        a = agg[(S, j, 1)]
        L.append(f"| {names[j]} | {fmt(a['alignment'], a['alignment_std'], True)} | {fmt(a['kappa'], a['kappa_std'], nd=3)} | {a['tokens_per_req']:.0f} |")
    summary["ablation"] = {j: agg[(S, j, 1)] for j in abl}
L += score_table("original", "Table 4. Published-label check: task 39, original OpenHands workspace, authors' consensus labels")

# label base rate (why kappa matters)
labels = [r["label"] for r in recs(judges[0], seeds_of[judges[0]][0], S)]
summary["base_rate_satisfied"] = sum(labels) / max(1, len(labels))
L.append(f"\nShare of requirements labelled satisfied (generated split): {100 * summary['base_rate_satisfied']:.1f}% "
         f"— a judge answering UNSATISFIED to everything would score {100 * (1 - summary['base_rate_satisfied']):.1f}% alignment, κ = 0.")

# blind-labelling check
started = min(v.get("started_utc", "9") for v in manifest["judges"].values())
late = []
for t in load_subset(cfg):
    p = label_path(cfg, t)
    if p.exists() and json.loads(p.read_text(encoding="utf-8")).get("labelled_at_utc", "") > started:
        late.append(t)
summary["labels_after_first_judge_run"] = late
L.append(f"\nLabels finished before the first judge run: {'yes' if not late else 'NO for ' + ', '.join(late)}.")
(run_dir / "tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ---------- figures ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
colors = {"llm_judge": "#6C7A96", "agent_judge": "#E09F3E", "agent_noread": "#3A7D7C"}
for j in judges:
    ks = sorted(k for (sp, jj, k) in agg if sp == S and jj == j)
    if not ks:
        continue
    xs = [agg[(S, j, k)]["tokens_per_req"] for k in ks]
    for ax, key in zip(axes, ("alignment", "kappa")):
        ys = [agg[(S, j, k)][key] * (100 if key == "alignment" else 1) for k in ks]
        es = [agg[(S, j, k)][key + "_std"] * (100 if key == "alignment" else 1) for k in ks]
        ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3, label=j, color=colors.get(j))
        for x, y, k in zip(xs, ys, ks):
            ax.annotate(f"k={k}", (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)
for ax, t in zip(axes, ("Alignment with labels (%)", "Cohen's κ")):
    ax.set_xlabel("tokens per requirement (prompt + completion)")
    ax.set_ylabel(t)
    ax.grid(alpha=0.3)
axes[0].legend()
fig.suptitle(f"Agreement vs. budget, mean ± std over seeds ({summary['n_requirements']['generated']} requirements)")
fig.tight_layout()
fig.savefig(run_dir / "fig1_budget_curve.png", dpi=200)

cats = sorted({r["category"] for r in recs(judges[0], seeds_of[judges[0]][0], S)})
fig, ax = plt.subplots(figsize=(10, 4))
width = 0.8 / max(1, len(judges))
for i, j in enumerate(judges):
    vals = []
    for c in cats:
        per = []
        for s in seeds_of[j]:
            rs = [r for r in recs(j, s, S) if r["category"] == c]
            per.append(alignment([r["label"] for r in rs], [vote(r, 1) for r in rs]) * 100 if rs else float("nan"))
        vals.append(sum(per) / len(per))
    ax.bar([x + i * width for x in range(len(cats))], vals, width, label=j, color=colors.get(j))
ax.set_xticks([x + width * (len(judges) - 1) / 2 for x in range(len(cats))])
ax.set_xticklabels(cats, rotation=20, ha="right", fontsize=8)
ax.set_ylabel("alignment % (k = 1)")
ax.legend()
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(run_dir / "fig2_by_category.png", dpi=200)

# ---------- failure cases ----------
F = ["# Failure cases: requirements the agent judge (k = 1) gets wrong in most seeds\n",
     "Open the trace file, read what `locate` returned and what evidence the verdict saw, and write the cause in the report.\n"]
if "agent_judge" in judges:
    wrong = defaultdict(list)
    for s in seeds_of["agent_judge"]:
        for key, r in records[("agent_judge", s)].items():
            if vote(r, 1) != r["label"]:
                wrong[key].append(s)
    n_seeds = len(seeds_of["agent_judge"])
    for (task, rid), ss in sorted(wrong.items(), key=lambda kv: -len(kv[1])):
        if len(ss) * 2 <= n_seeds:
            continue
        r = records[("agent_judge", ss[0])][(task, rid)]
        loc = next((st.get("paths") for st in r["steps"] if st["step"] == "locate"), [])
        trace = TRACES / args.run_id / "agent_judge" / f"seed_{ss[0]}" / f"{task}__R{rid}.json"
        F.append(f"- **{task} R{rid}** ({r['category']}) label={'SAT' if r['label'] else 'UNSAT'}, wrong in seeds {ss}; "
                 f"located {loc}\n  - criteria: {r['criteria']}\n  - trace: `{trace.relative_to(TRACES.parent).as_posix()}`")
    summary["n_failure_cases"] = sum(1 for v in wrong.values() if len(v) * 2 > n_seeds)
(run_dir / "failure_cases.md").write_text("\n".join(F) + "\n", encoding="utf-8")

summary["agg"] = {f"{sp}|{j}|{k}": v for (sp, j, k), v in agg.items()}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
print((run_dir / "tables.md").read_text(encoding="utf-8"))
print(f"figures, failure cases and summary.json written to {run_dir}")
