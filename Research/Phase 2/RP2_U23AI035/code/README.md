# Agent-as-a-Judge vs. budget-matched LLM-as-a-Judge on DevAI

AI465 Agentic AI · Research Project Phase 2 · U23AI035

**Objective (approved in Phase 1, scope change in section 2):** evaluate Agent-as-a-Judge
(locate + read + ask, black-box) on an open-weight backbone, Qwen2.5-7B-Instruct via Ollama,
for requirement-level judging of DevAI workspaces, compared against LLM-as-a-Judge with
majority voting over k samples at a matched token budget. The measures are alignment rate and
Cohen's κ against human labels, plus calls, tokens and latency per requirement.

---

## 1. What is compared

The two judges use **the same model, the same decoding settings and the same judging prompt**
(`prompts/judge_system.txt`, `prompts/judge_user.txt`). They differ in one thing only: how
the evidence placed in `{evidence}` is gathered.

| Judge | Evidence | Model calls per requirement |
|---|---|---|
| `llm_judge` (baseline) | the whole workspace: tree, then every file, capped at 12k tokens | k verdict samples |
| `agent_judge` (method) | tree, plus the files an LLM `locate` step picked, opened by `read` | 1 locate + k verdict samples |
| `agent_noread` (ablation) | tree plus located paths, without file contents | 1 locate + k verdict samples |

Every judge draws `k_max = 5` verdict samples per requirement and stores them all. Majority
voting for any k ≤ 5, and its cost, is then computed offline in `05_analyze.py`. That makes
the matched-budget comparison exact: the baseline's k is chosen so that its tokens per
requirement are closest to the agent's.

## 2. Deviations from the Phase 1 objective (declared)

| Planned in Phase 1 | Done | Why |
|---|---|---|
| Judge the original OpenHands outputs for all 55 DevAI tasks against the authors' human labels | The original outputs are used for **task 39 only** (7 requirements, authors' labels). The main set is **20 tasks whose workspaces we generate** with a local developer agent and **label ourselves** (`03_label.py`). | The authors released the workspace of only one task. GitHub issue #36 (opened 2025-12-30, still unanswered 2026-10-14) asks for the rest. The labels cannot be used without the outputs they describe. |
| Multimodal `read` | Images are described by type and size; PDFs are read as text | Qwen2.5-7B is text-only |
| `graph` module | Replaced by a plain directory tree | The paper's graph is used for code search, which it found did not help on DevAI-sized workspaces (App. K) |

The developer agent runs `llama3.1:8b-instruct`, a different family from the judge, so the
judge never grades its own model's output (Phase 2 judging rule; Gap 3 in Phase 1).

## 3. Environment

* Windows 11 or Linux, Python 3.10/3.11, [Ollama](https://ollama.com) ≥ 0.4, git
* GPU recommended (any NVIDIA card with ≥ 8 GB runs both 7–8B models at Q4); CPU works but is about 10× slower
* Docker Desktop, only needed if the developer agent should execute code (section 4, step 3)
* **No API keys.** `.env.example` lists the optional variables `OLLAMA_HOST` and `AAJ_SANDBOX`.

Install:

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b-instruct-q4_K_M
python scripts/check_env.py
python -m pytest -q
```

## 4. Reproducing every result

| Step | Command | Time (RTX-class GPU) | Who |
|---|---|---|---|
| 1 | `python scripts/00_fetch_devai.py` (clones DevAI at the pinned commit) | 1 min | auto |
| 2 | `python scripts/01_select_tasks.py` (fixed 20-task subset, seed 465) | seconds | auto |
| 3 | `python scripts/02_generate_workspaces.py` (developer agent, 30 min cap per task) | 2–6 h | auto |
| 4 | `python scripts/03_label.py --labeler U23AI035` (blind hand-labelling) | 3–4 h | **you** |
| 5 | `python scripts/04_run_judges.py --judge llm_judge` | 3–5 h | auto |
| 6 | `python scripts/04_run_judges.py --judge agent_judge` | 1–2 h | auto |
| 7 | `python scripts/04_run_judges.py --judge agent_noread --k 1` | 20 min | auto |
| 8 | `python scripts/05_analyze.py` (all tables, figures, failure cases) | seconds | auto |
| 9 | `python scripts/06_build_report.py` (fills the report template) | seconds | auto |

`run_all.ps1` / `run_all.sh` chain steps 1, 2 and 5–9. Steps 3 and 4 are left commented out
because they need you.

**Step 3, executing code safely.** By default the developer agent only writes files (its
`run` actions are refused), which is safe but produces workspaces without results files. To
let it run its code, use the Docker sandbox so model-written commands never run on your PC:

```bash
docker build -f docker/Dockerfile.devagent -t aaj-devagent .
docker run --rm -it -v "${PWD}:/repo" -e OLLAMA_HOST=http://host.docker.internal:11434 aaj-devagent
```

Whichever mode you use, report it: it is stored in `data/trajectories/<model>/_generation_log.json`.

**Approximate cost.** API cost is $0. The judges make about 4,600 local calls (≈140
requirements × 3 seeds × [5 baseline + 6 agent] + ablation; the exact count is printed by `01_select_tasks.py`). The developer agent makes at most
25 calls per task. Total runtime is roughly 8–14 h on a laptop GPU, most of it unattended.

**Smoke test (2 minutes):** `python scripts/04_run_judges.py --judge agent_judge --split original --limit 2 --seeds 11 --k 1 --run-id smoke`

**Demo for the viva:** `python scripts/demo.py` judges one requirement of task 39 with both judges and prints locate → read → votes.

## 5. Pinned configuration and outputs

* Everything is set in `configs/experiment.yaml`: models, temperature 0.7, top-p 0.9, seeds 11/22/33, k_max 5, context 16k, token caps, and the DevAI commit `43c2fa7`.
* `results/<run_id>/manifest.json` adds the Ollama model digest, the run dates, and the Python and OS versions.
* Prompt tokens are counted with the Qwen2.5 tokenizer, not Ollama's `prompt_eval_count`. Ollama omits tokens served from its prompt cache, which would make repeated votes look free. Both numbers are saved.
* Raw results: `results/<run_id>/<judge>/seed_<s>.jsonl`, one record per requirement with every sample's verdict and cost.
* Traces: `traces/<run_id>/<judge>/seed_<s>/<task>__R<i>.json`, with every prompt, output, located path and token count.
* Developer trajectories: `data/trajectories/<model>/<task>.json`, in the DevAI trajectory schema.

## 6. What is mine and what is borrowed

| Part | Source |
|---|---|
| `prompts/judge_*.txt`, `prompts/locate_*.txt` | Copied verbatim from [metauto-ai/agent-as-a-judge](https://github.com/metauto-ai/agent-as-a-judge) (MIT) so the judge matches the paper |
| DevAI tasks, task-39 workspace, human labels | Same repository, fetched at runtime and not redistributed |
| Everything else: `aaj/*` (Ollama client, token accounting, workspace reader, both judges, ablation, offline voting and metrics, developer agent), all `scripts/*`, tests, the analysis | Written for this project. No agent framework is used. |

The upstream implementation was read but not imported. The judges here are a ~150-line
re-implementation of its black-box locate → read → ask path, so that both judges share one
prompt and one cost accounting.
