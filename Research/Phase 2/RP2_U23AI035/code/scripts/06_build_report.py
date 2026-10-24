"""Fill the report template with the numbers in results/<run_id>/ and export it.

  python scripts/06_build_report.py [--run-id main]

Reads  ../report/RP2_report_template.md
Writes ../report/RP2_U23AI035_report.md  (+ .docx via pandoc, if pandoc is installed)
Every {{PLACEHOLDER}} that has a value is replaced; the analysis paragraphs marked
"WRITE:" are yours to write after reading the tables, figures and failure cases.
"""
import argparse
import json
import re
import shutil
import subprocess

import _bootstrap  # noqa: F401
from aaj.config import RESULTS, ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--run-id", default="main")
args = ap.parse_args()
run = RESULTS / args.run_id
S = json.loads((run / "summary.json").read_text(encoding="utf-8"))
A = S["agg"]


def g(key, field, pct=False, nd=1):
    a = A.get(key)
    if not a:
        return "n/a"
    m, s = a[field], a[field + "_std"]
    return f"{100 * m:.{nd}f} ± {100 * s:.{nd}f}" if pct else f"{m:.{nd}f} ± {s:.{nd}f}"


vals = {
    "TABLES": (run / "tables.md").read_text(encoding="utf-8").split("\n", 1)[1],
    "N_TASKS": S["n_tasks"], "N_REQ_GEN": S["n_requirements"]["generated"], "N_REQ_ORIG": S["n_requirements"]["original"],
    "MODEL": S["model"]["model"], "DIGEST": S["model"].get("digest"),
    "BASE_RATE": f"{100 * S['base_rate_satisfied']:.1f}",
    "ALWAYS_NO": f"{100 * (1 - S['base_rate_satisfied']):.1f}",
    "AGENT_ALIGN_K1": g("generated|agent_judge|1", "alignment", True), "LLM_ALIGN_K1": g("generated|llm_judge|1", "alignment", True),
    "AGENT_KAPPA_K1": g("generated|agent_judge|1", "kappa", nd=3), "LLM_KAPPA_K1": g("generated|llm_judge|1", "kappa", nd=3),
    "AGENT_TOK_K1": g("generated|agent_judge|1", "tokens_per_req", nd=0), "LLM_TOK_K1": g("generated|llm_judge|1", "tokens_per_req", nd=0),
    "ORIG_AGENT_ALIGN": g("original|agent_judge|1", "alignment", True), "ORIG_LLM_ALIGN": g("original|llm_judge|1", "alignment", True),
    "N_FAILURES": S.get("n_failure_cases", "n/a"),
}
if "matched" in S:
    vals["K_MATCHED_LLM"] = S["matched"]["agent@1_vs_llm@k"]["k_llm"]
    vals["K_MATCHED_AGENT"] = S["matched"]["llm@1_vs_agent@k"]["k_agent"]
tpl = (ROOT.parent / "report" / "RP2_report_template.md").read_text(encoding="utf-8")
out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(vals.get(m.group(1), m.group(0))), tpl)
left = sorted(set(re.findall(r"\{\{(\w+)\}\}", out)))
dst = ROOT.parent / "report" / "RP2_U23AI035_report.md"
dst.write_text(out, encoding="utf-8")
print(f"wrote {dst}" + (f"; unfilled placeholders: {left}" if left else ""))
for fig in ("fig1_budget_curve.png", "fig2_by_category.png"):
    if (run / fig).exists():
        shutil.copy(run / fig, dst.parent / fig)
if shutil.which("pandoc"):
    subprocess.run(["pandoc", dst.name, "-o", dst.with_suffix(".docx").name, "--resource-path=."],
                   cwd=dst.parent, check=False)
    print(f"wrote {dst.with_suffix('.docx')}  (open in Word, finish the WRITE: sections, export to PDF)")
else:
    print("pandoc not found: open the .md in VS Code / Typora, or install pandoc, to make a .docx/.pdf")
