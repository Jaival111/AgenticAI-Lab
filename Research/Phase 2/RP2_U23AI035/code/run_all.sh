# Regenerates every number in the report from a clean checkout (bash).
# Steps 02 and 03 need you (sandbox + hand labelling); everything after is automatic.
set -e
python scripts/check_env.py
python scripts/00_fetch_devai.py
python scripts/01_select_tasks.py
# python scripts/02_generate_workspaces.py        # see README section 4 (Docker recommended)
# python scripts/03_label.py --labeler U23AI035   # label BEFORE judging
python scripts/04_run_judges.py --judge llm_judge
python scripts/04_run_judges.py --judge agent_judge
python scripts/04_run_judges.py --judge agent_noread --k 1
python scripts/05_analyze.py
python scripts/06_build_report.py
