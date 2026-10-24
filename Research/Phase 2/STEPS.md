# Phase 2: your step-by-step checklist

Everything lives in `RP2_U23AI035/`:

* `code/`: the repository you submit
* `report/`: the report template
* `slides/`: the 10-slide deck, with numbers filled in automatically after the runs

Nothing has been run yet. The only checks so far were a syntax check of the Python files and a test build of the slides.

---

## Week 5, before anything else: get the data change approved

The DevAI authors released the developer-agent output for **only 1 of 55 tasks** (task 39). Their human labels for the other 54 refer to outputs nobody can download; see GitHub issue #36 on metauto-ai/agent-as-a-judge. Your Phase 1 objective therefore cannot be run on "all 55 tasks with the authors' labels".

Phase 2 rules say a change needs **prior approval and a technical reason**. Send your instructor something like:

> My approved objective compares Agent-as-a-Judge with budget-matched LLM-as-a-Judge on DevAI. The authors released the OpenHands workspace for only task 39 (GitHub issue #36, open since Dec 2025), so the human labels for the other tasks cannot be used. I propose to keep the objective, methods, model and metrics unchanged. I would generate workspaces for 20 DevAI tasks with a local developer agent and label their ~140 requirements myself, blind, before judging. Task 39 would be judged against the authors' original labels as a published-label check. May I proceed?

Write the approval date into report section 1 and slide 2.

## Week 5: set up (about 1 hour)

Open a terminal in `RP2_U23AI035/code`, then run each command:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b-instruct-q4_K_M
python scripts/check_env.py
python -m pytest -q
python scripts/00_fetch_devai.py
python scripts/01_select_tasks.py
```

You should see these results:

* `check_env.py` prints `[ok]` for Ollama, both models, and the token counting mode.
* `pytest` reports 9 tests passed.
* `00_fetch_devai.py` reports 55 instances and that the task-39 workspace is present.
* `01_select_tasks.py` prints the number of requirements. Note it down; it is the "N" in your report.

**Smoke test (2 minutes).** This proves that the judges, traces and cost logging work:

```bash
python scripts/04_run_judges.py --judge agent_judge --split original --limit 2 --seeds 11 --k 1 --run-id smoke
```

Then open `traces/smoke/agent_judge/seed_11/` and read one file.

## Week 5–6: generate the workspaces (2–6 h, unattended)

You have a choice of two modes:

* **Safe mode.** The agent writes files but never runs them, so there are no result files in the workspaces:
  ```bash
  python scripts/02_generate_workspaces.py
  ```
* **Recommended: Docker sandbox.** The agent can also run its code. Start Docker Desktop first, then:
  ```bash
  docker build -f docker/Dockerfile.devagent -t aaj-devagent .
  ```
  ```bash
  docker run --rm -it -v "${PWD}:/repo" -e OLLAMA_HOST=http://host.docker.internal:11434 aaj-devagent
  ```

Do **not** use `--i-understand-exec-risk` outside Docker: it runs model-written shell commands on your laptop.

If it stops partway, run the same command again; finished tasks are skipped. Write down which mode you used for the report.

## Week 6: label, BEFORE any judge run (3–4 h, by you)

```bash
python scripts/03_label.py --labeler U23AI035
```

For each requirement press `y` or `n`. Use `o` to open files and `t` to see the tree. Follow the rule printed at the top: judge each requirement on its own, and the file must exist at the requested path with real content. `q` saves your progress, so you can do it in several sittings. `05_analyze.py` later checks automatically that every label was written before the first judge run.

## Week 6–8: run the experiment (6–9 h, unattended; overnight is fine)

```bash
python scripts/04_run_judges.py --judge llm_judge
```
```bash
python scripts/04_run_judges.py --judge agent_judge
```
```bash
python scripts/04_run_judges.py --judge agent_noread --k 1
```

Each command runs 3 seeds over all requirements and resumes if interrupted. The baseline (`llm_judge`) is the "build the baseline first" step. After it finishes, run `05_analyze.py` once and look at Table 4 (task 39). It compares your baseline against the paper's 60.4%; if the numbers differ, write down why. The likely cause is the model (7B vs GPT-4o).

## Week 8: analyse and write

```bash
python scripts/05_analyze.py
```
```bash
python scripts/06_build_report.py
```
```bash
cd ../slides && npm install && node build_slides.js
```

* `results/main/tables.md`, `fig1_budget_curve.png` and `fig2_by_category.png` are all your results.
* `results/main/failure_cases.md` lists misjudged requirements. Open one listed trace and explain the cause; this is required for the report and slide 8.
* `report/RP2_U23AI035_report.md` and `.docx` come with numbers filled in. Write every **WRITE:** paragraph yourself, keep the report within 4 pages, and export it to PDF.
* `slides/RP2_U23AI035_slides.pptx` is rebuilt with numbers and Figure 1. Fill slide 6's takeaway and slide 8's failure case by hand.

## Week 9: demo and submission

* Live demo:
  ```bash
  python scripts/demo.py
  ```
  Also record a backup of at most 3 minutes, for example with Win+G.
* Fill in your name on slides 1 and 10.
* The submission zip (`RP2_U23AI035.zip`) holds the report PDF, the slides and `code/`. `code/` includes `results/`, `traces/` and `data/` (workspaces, trajectories, labels); leave out `data/devai_repo` and `.venv`. This folder does not create the zip; you will.

## Know your code for the viva

You must be able to explain any line. Read these files in this order:

1. `aaj/judges.py`: both judges and the ablation, about 150 lines
2. `aaj/metrics.py`: voting, κ and cost
3. `scripts/04_run_judges.py`: seeds, traces and resume
4. `scripts/05_analyze.py`: how the matched k is chosen
5. `aaj/llm.py` and `aaj/tokens.py`: why prompt tokens are counted with the tokenizer and not taken from Ollama
