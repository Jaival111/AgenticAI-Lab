---
title: "Agent-as-a-Judge vs. Budget-Matched LLM-as-a-Judge on DevAI with an Open-Weight Model"
subtitle: "AI465 Agentic AI · Research Project Phase 2 · U23AI035"
---

<!--
HOW TO USE THIS TEMPLATE
1. After running the experiments, run:  python scripts/06_build_report.py   (from code/)
   -> writes RP2_U23AI035_report.md/.docx with every {{PLACEHOLDER}} filled.
2. Replace every "WRITE:" paragraph with your own analysis (the rules forbid LM-written analysis).
3. Keep the whole report within 4 pages: trim Table 3/4 rows if needed, keep Figure 1.
-->

## 1. Objective (restated) and declared deviations

**Approved objective.** To evaluate Agent-as-a-Judge (locate + read + ask, black-box setting) on an open-weight backbone, Qwen2.5-7B-Instruct served locally through Ollama, for requirement-level judging on DevAI, compared against LLM-as-a-Judge with majority voting over *k* samples at a matched token budget, measured by alignment rate and Cohen's κ against human labels and by LLM calls, tokens and wall-clock latency per requirement. It addresses Gap 1 of Phase 1: the paper never gave the LLM-as-a-Judge baseline the agent's budget.

**Deviation (declared).** The DevAI authors released the developer-agent workspace for only one of the 55 tasks (task 39; the request for the rest, GitHub issue #36, is unanswered). The human labels for the other 54 tasks therefore cannot be paired with the outputs they describe. I kept the objective and changed the data:

* (a) **Main set:** {{N_TASKS}} DevAI tasks ({{N_REQ_GEN}} requirements). A local developer agent (Llama-3.1-8B, a different model family from the judge) generated the workspaces and I labelled every requirement by hand before running any judge.
* (b) **Published-label check:** task 39 on the original OpenHands workspace with the authors' consensus labels ({{N_REQ_ORIG}} requirements).

WRITE: one sentence stating whether the instructor approved this change and when.

## 2. What was implemented

Both judges call the same model with the same judging prompt, copied verbatim from the authors' repository. They differ only in how the evidence placed in that prompt is gathered:

* **LLM-as-a-Judge (baseline)** sees a dump of the whole workspace (tree, then every file, capped at 12k tokens).
* **Agent-as-a-Judge (method)** first calls a *locate* step that returns up to five file paths from the workspace tree, then *reads* those files (2k tokens each) and asks for a verdict.
* **Ablation (`agent_noread`)** keeps *locate* but removes *read*.

Each judge draws five verdict samples per requirement and saves them all. Majority voting for *k* = 1…5, and its cost, is computed offline from the saved samples, so one run gives a full accuracy-versus-tokens curve. The budget-matched *k* is then chosen from that curve. Prompt tokens are counted with the Qwen2.5 tokenizer rather than taken from Ollama, whose prompt cache would otherwise make repeated votes look free.

I wrote everything except the prompts and the DevAI data, without an agent framework. That covers the Ollama client, token accounting, workspace reader, the three judges, the developer agent, the labelling tool, metrics and analysis (about 900 lines; see the README for the split).

## 3. Experimental setup (pinned)

| Item | Value |
|---|---|
| Judge model | `{{MODEL}}`, Ollama digest `{{DIGEST}}` |
| Decoding | temperature 0.7, top-p 0.9, context 16,384, max 512 new tokens |
| Seeds / runs | 11, 22, 33 (three full runs of every configuration); sample *i* uses seed `run×1000+i` |
| Votes | *k*_max = 5 samples stored; *k* ∈ {1, 3, 5} reported |
| Developer agent | `llama3.1:8b-instruct-q4_K_M`, temperature 0.2, ≤ 25 steps, 30-min limit; code execution: WRITE: on (Docker) / off |
| Data | DevAI at commit `43c2fa7`; {{N_TASKS}} tasks without Kaggle/web needs, selected with seed 465 |
| Labels | binary, one labeller (me), rules of DevAI evaluator 38bb (paper App. H), all finished before the first judge run |
| Hardware / dates | WRITE: GPU, RAM, dates of the runs |

## 4. Results

{{TABLES}}

![Figure 1. Agreement with human labels versus tokens per requirement, for k = 1…5 (mean ± std over three runs).](fig1_budget_curve.png)

![Figure 2. Alignment by requirement category, k = 1.](fig2_by_category.png)

## 5. Analysis

**Base rate.** {{BASE_RATE}}% of requirements were labelled satisfied. A judge that always answers UNSATISFIED would therefore already score {{ALWAYS_NO}}% alignment, with κ = 0. This is why κ, and not only alignment, is reported (Phase 1 Gap 4).

**Main comparison.**

| Judge (*k* = 1) | Alignment | κ | Tokens per requirement |
|---|---|---|---|
| Agent-as-a-Judge | {{AGENT_ALIGN_K1}}% | {{AGENT_KAPPA_K1}} | {{AGENT_TOK_K1}} |
| LLM-as-a-Judge | {{LLM_ALIGN_K1}}% | {{LLM_KAPPA_K1}} | {{LLM_TOK_K1}} |

At matched budget, the baseline needs *k* = {{K_MATCHED_LLM}} votes to spend what the agent spends, and the agent needs *k* = {{K_MATCHED_AGENT}} to spend what one baseline call spends (Table 2).

WRITE (3–5 sentences): Interpret, do not restate. Does the agent still win once the budget is matched? Is the difference larger than the std across seeds? Which costs more, and does the conclusion of the paper (agent ≫ LLM judge) survive with a 7B open model? A null or negative result is acceptable; say so plainly.

**Ablation.** WRITE (2–3 sentences, from Table 3): how much of the difference is due to *reading* the located files, as opposed to *locating* them or to the whole-workspace dump?

**Published-label check (task 39, Table 4).** Agent judge {{ORIG_AGENT_ALIGN}}%, LLM judge {{ORIG_LLM_ALIGN}}% on {{N_REQ_ORIG}} requirements. The paper reports 90.4% and 60.4% (black-box, OpenHands, all 55 tasks, GPT-4o). WRITE: are we in the same range? Seven requirements is too few to conclude; say what it does and does not show, and name the model-version difference as the likely cause of any gap.

**Failure case read from a trace.** {{N_FAILURES}} requirements were misjudged by the agent in most seeds (`results/main/failure_cases.md`). WRITE (one paragraph): pick one, open its trace file, and explain the cause step by step. For example: *locate* returned a path that does not exist, so *read* opened nothing and the verdict relied on the tree alone; or the file was read but truncated before the relevant code. Quote the trace path.

## 6. Limitations

WRITE, starting from these facts:

* Labels come from one labeller (me), with no second rater. Agreement is with *my* reading of the requirements.
* The workspaces come from a weaker developer than the paper's, so they may be easier or harder to judge than OpenHands outputs.
* Only one judge model and one domain were tested. Images are not seen by a text-only judge.
* Temperature 0.7 is needed for voting but adds variance at *k* = 1.

## 7. With four more weeks

WRITE: e.g.

* a second labeller on a subset, with inter-rater κ;
* a second judge family (Llama/Mistral) to test Phase 1 Gap 3;
* the gray-box setting using the saved developer trajectories;
* asking the authors again for the original workspaces.

*Use of language models:* WRITE one honest line on how you used them.
