// Builds RP2_U23AI035_slides.pptx (10 slides, same visual style as Phase 1).
//   npm install            (once, in this folder)
//   node build_slides.js   (re-run after `python scripts/05_analyze.py`)
// If ../code/results/main/summary.json exists, numbers and figures are filled in;
// otherwise every result is a clearly marked [placeholder].
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const RUN = path.resolve(__dirname, "../code/results/main");
const S = fs.existsSync(path.join(RUN, "summary.json")) ? JSON.parse(fs.readFileSync(path.join(RUN, "summary.json"), "utf8")) : null;
const A = (S && S.agg) || {};
const pct = (key, f = "alignment") => (A[key] ? `${(100 * A[key][f]).toFixed(1)} ± ${(100 * A[key][f + "_std"]).toFixed(1)}%` : "[fill]");
const num = (key, f, nd = 0) => (A[key] ? `${A[key][f].toFixed(nd)}` : "[fill]");
const kap = (key) => (A[key] ? `${A[key].kappa.toFixed(2)} ± ${A[key].kappa_std.toFixed(2)}` : "[fill]");
const fig = (name) => (fs.existsSync(path.join(RUN, name)) ? path.join(RUN, name) : null);

const H = { ink: "1B2A41", ink2: "33415C", paper: "FFFFFF", mist: "EEF1F6", amber: "E09F3E", teal: "3A7D7C", red: "9E2A2B", slate: "6C7A96", ice: "C9D3E3", sand: "F6E3C3" };
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };
pres.title = "AI465 RP2 - Agent-as-a-Judge vs budget-matched LLM-as-a-Judge";
pres.author = "U23AI035";

pres.defineSlideMaster({ title: "DARK", background: { color: H.ink }, objects: [] });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: H.paper },
  objects: [{ text: { text: "AI465 Agentic AI · Research Project Phase 2 · U23AI035", options: { x: 0.5, y: 5.2, w: 6, h: 0.3, fontSize: 10, color: H.slate, margin: 0 } } }],
  slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: H.slate, align: "right" },
});

let n = 0;
const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: H.ink2, valign: "top", fontFace: "Calibri" }, o, { objectName: `t${++n}` }));
const R = (s, o) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ line: { type: "none" }, rectRadius: 0.08 }, o, { objectName: `r${++n}` }));
const badge = (s, x, y, label, fill, d = 0.5, fs = 13) => {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: `b${++n}` });
  T(s, label, { x, y, w: d, h: d, fontSize: fs, bold: true, color: H.paper, align: "center", valign: "middle" });
};
const title = (s, text) => T(s, text, { x: 0.5, y: 0.3, w: 9, h: 0.75, fontSize: 28, bold: true, color: H.ink, fontFace: "Cambria", valign: "middle" });
const placeholder = (s, x, y, w, h, label) => {
  R(s, { x, y, w, h, fill: { color: H.mist }, line: { color: H.slate, width: 1, dashType: "dash" } });
  T(s, label, { x: x + 0.2, y, w: w - 0.4, h, fontSize: 13, italic: true, color: H.slate, align: "center", valign: "middle" });
};
const imageOr = (s, file, x, y, w, h, label) => (fig(file) ? s.addImage({ path: fig(file), x, y, w, h, sizing: { type: "contain", w, h }, altText: label, objectName: `img${++n}` }) : placeholder(s, x, y, w, h, `[${label}]\nresults/main/${file}`));

// 1. Title
let s = pres.addSlide({ masterName: "DARK" });
T(s, "AI465 RESEARCH PROJECT · PHASE 2", { x: 0.6, y: 0.75, w: 8.8, h: 0.4, fontSize: 14, bold: true, color: H.amber, charSpacing: 2 });
T(s, "Does Agent-as-a-Judge still win at a matched budget on a 7B open model?", { x: 0.6, y: 1.35, w: 8.8, h: 1.6, fontSize: 34, bold: true, color: H.paper, fontFace: "Cambria", valign: "bottom" });
T(s, "Implementation and evaluation of the Phase 1 objective · DevAI · Qwen2.5-7B via Ollama", { x: 0.6, y: 3.15, w: 8.8, h: 0.8, fontSize: 18, color: H.ice });
T(s, "Name: ____________________     Roll No.: U23AI035", { x: 0.6, y: 4.6, w: 8.8, h: 0.4, fontSize: 14, color: H.paper });
s.addNotes("30 s. Restate the question from Phase 1: the paper's agent judge beat an LLM judge that was never given the same budget. I rebuilt both on a local 7B model and compared them at equal tokens.");

// 2. Objective and deviation
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Objective, and one declared change of data");
R(s, { x: 0.5, y: 1.2, w: 9, h: 1.5, fill: { color: H.ink } });
T(s, [{ text: "Objective: ", options: { bold: true, color: H.amber } }, { text: "Agent-as-a-Judge (locate + read + ask) vs LLM-as-a-Judge with k-vote majority at a matched token budget, same open-weight model, on DevAI; alignment and Cohen's κ against human labels, plus calls, tokens and latency per requirement.", options: { color: H.paper } }],
  { x: 0.8, y: 1.3, w: 8.4, h: 1.3, fontSize: 15, valign: "middle" });
R(s, { x: 0.5, y: 2.95, w: 9, h: 2.05, fill: { color: H.sand } });
badge(s, 0.75, 3.15, "!", H.red, 0.5, 18);
T(s, "The authors released the developer-agent workspace for 1 of 55 tasks (GitHub issue #36, unanswered).", { x: 1.45, y: 3.12, w: 7.8, h: 0.55, fontSize: 14, bold: true, color: H.ink });
T(s, [
  { text: `Main set: ${S ? S.n_tasks : "20"} tasks, workspaces generated by a local Llama-3.1-8B developer, labelled blind by me (${S ? S.n_requirements.generated : "[n]"} requirements)`, options: { bullet: true, breakLine: true } },
  { text: `Published-label check: task 39, original OpenHands workspace, authors' labels (${S ? S.n_requirements.original : "7"} requirements)`, options: { bullet: true } },
], { x: 1.45, y: 3.7, w: 7.8, h: 1.2, fontSize: 13, paraSpaceAfter: 4 });
s.addNotes("60 s. Say this up front: the objective is unchanged, the data changed for a demonstrated technical reason, approved by the instructor on [date]. The developer model is a different family from the judge, so the judge never grades itself.");

// 3. What was built
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Same model and prompt; only evidence differs");
const rows = [
  ["LLM-as-a-Judge", "baseline", H.slate, "whole workspace dump (≤ 12k tokens)", "k votes"],
  ["Agent-as-a-Judge", "method", H.amber, "tree → locate (LLM) → read located files", "1 + k calls"],
  ["agent_noread", "ablation", H.teal, "tree → locate, file contents withheld", "1 + k calls"],
];
rows.forEach((r, i) => {
  const y = 1.25 + i * 1.05;
  R(s, { x: 0.5, y, w: 9, h: 0.85, fill: { color: H.mist } });
  badge(s, 0.7, y + 0.17, String(i + 1), r[2], 0.5);
  T(s, [{ text: r[0], options: { bold: true, color: H.ink, breakLine: true } }, { text: r[1], options: { fontSize: 11, color: H.slate } }], { x: 1.35, y: y + 0.1, w: 2.3, h: 0.65, fontSize: 15, valign: "middle" });
  T(s, r[3], { x: 3.75, y: y + 0.1, w: 4.2, h: 0.65, fontSize: 14, valign: "middle" });
  T(s, r[4], { x: 8.0, y: y + 0.1, w: 1.35, h: 0.65, fontSize: 13, bold: true, color: H.ink, valign: "middle", align: "right" });
});
T(s, "5 votes stored per requirement → majority for any k ≤ 5 computed offline → exact budget matching. Prompt tokens counted with the Qwen tokenizer (Ollama's cache hides repeats).", { x: 0.5, y: 4.45, w: 9, h: 0.6, fontSize: 12, italic: true, color: H.red });
s.addNotes("60 s. One component differs between baseline and method: evidence gathering. The judging prompt is the authors' own. Explain why storing all votes lets me match budgets after the fact, and why I count tokens myself.");

// 4. Protocol
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Protocol: pinned, repeated, traced");
const cells = [
  ["Model", S ? `${S.model.model}` : "qwen2.5:7b-instruct", S && S.model.digest ? `digest ${String(S.model.digest).slice(0, 12)}` : "digest in manifest.json"],
  ["Decoding", "T 0.7 · top-p 0.9", "ctx 16k · ≤ 512 new tokens"],
  ["Runs", "3 seeds (11, 22, 33)", "mean ± std everywhere"],
  ["Labels", "blind, before any judge run", "DevAI rules (App. H, 38bb)"],
  ["Traces", "every prompt + output on disk", "traces/main/<judge>/seed_*/"],
  ["Cost", "$0 API · local GPU", "tokens + latency per requirement"],
];
cells.forEach((c, i) => {
  const x = 0.5 + (i % 3) * 3.07, y = 1.25 + Math.floor(i / 3) * 1.9;
  R(s, { x, y, w: 2.86, h: 1.7, fill: { color: H.mist } });
  T(s, c[0].toUpperCase(), { x: x + 0.2, y: y + 0.18, w: 2.5, h: 0.3, fontSize: 11, bold: true, color: H.teal, charSpacing: 1 });
  T(s, c[1], { x: x + 0.2, y: y + 0.55, w: 2.5, h: 0.6, fontSize: 15, bold: true, color: H.ink });
  T(s, c[2], { x: x + 0.2, y: y + 1.15, w: 2.5, h: 0.4, fontSize: 11, color: H.ink2 });
});
s.addNotes("45 s. These are the Phase 2 protocol requirements: three runs with variance, pinned configuration, prompts as files, cost reported, full traces. Everything regenerates from run_all.ps1.");

// 5. Main result figure
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Agreement vs budget (generated set)");
imageOr(s, "fig1_budget_curve.png", 0.5, 1.15, 6.3, 3.9, "Figure 1: agreement vs tokens per requirement");
const stat = [["Agent @ k=1", pct("generated|agent_judge|1"), `κ ${kap("generated|agent_judge|1")} · ${num("generated|agent_judge|1", "tokens_per_req")} tok`, H.amber],
  ["LLM @ k=1", pct("generated|llm_judge|1"), `κ ${kap("generated|llm_judge|1")} · ${num("generated|llm_judge|1", "tokens_per_req")} tok`, H.slate]];
stat.forEach((st, i) => {
  const y = 1.2 + i * 1.95;
  R(s, { x: 7.0, y, w: 2.5, h: 1.75, fill: { color: H.mist } });
  T(s, st[0], { x: 7.2, y: y + 0.15, w: 2.1, h: 0.3, fontSize: 12, bold: true, color: H.ink });
  T(s, st[1], { x: 7.2, y: y + 0.5, w: 2.2, h: 0.6, fontSize: 18, bold: true, color: st[3], fontFace: "Cambria" });
  T(s, st[2], { x: 7.2, y: y + 1.15, w: 2.1, h: 0.5, fontSize: 11 });
});
s.addNotes("75 s. Read the figure: x is tokens per requirement, y is agreement. Each point is a k. The question is which curve is higher at the same x. State the result plainly, including if the agent does NOT win.");

// 6. Matched budget + ablation
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Matched budget and ablation");
const m = S && S.matched;
const tbl = (x, y, w, head, body) => s.addTable([head.map((h) => ({ text: h, options: { bold: true, color: H.paper, fill: { color: H.ink } } })), ...body],
  { x, y, w, fontSize: 12, fontFace: "Calibri", color: H.ink2, border: { type: "solid", color: "D5DAE3", pt: 0.75 }, rowH: 0.42, objectName: `tbl${++n}` });
T(s, "Table 2 · equal tokens", { x: 0.5, y: 1.15, w: 4.4, h: 0.35, fontSize: 14, bold: true, color: H.ink });
tbl(0.5, 1.55, 4.4, ["Pair", "Agent", "LLM"], m ? [
  [`agent@1 vs llm@${m["agent@1_vs_llm@k"].k_llm}`, `${(100 * m["agent@1_vs_llm@k"].agent.alignment).toFixed(1)}%`, `${(100 * m["agent@1_vs_llm@k"].llm.alignment).toFixed(1)}%`],
  [`agent@${m["llm@1_vs_agent@k"].k_agent} vs llm@1`, `${(100 * m["llm@1_vs_agent@k"].agent.alignment).toFixed(1)}%`, `${(100 * m["llm@1_vs_agent@k"].llm.alignment).toFixed(1)}%`]]
  : [["agent@1 vs llm@k*", "[fill]", "[fill]"], ["agent@k* vs llm@1", "[fill]", "[fill]"]]);
T(s, "Table 3 · what the agent's evidence adds (k = 1)", { x: 5.1, y: 1.15, w: 4.4, h: 0.35, fontSize: 14, bold: true, color: H.ink });
tbl(5.1, 1.55, 4.4, ["Evidence", "Align.", "κ"], [
  ["whole dump", pct("generated|llm_judge|1"), kap("generated|llm_judge|1")],
  ["tree + paths", pct("generated|agent_noread|1"), kap("generated|agent_noread|1")],
  ["tree + files read", pct("generated|agent_judge|1"), kap("generated|agent_judge|1")]]);
placeholder(s, 0.5, 3.6, 9, 1.35, "[One-sentence takeaway: is the gain from reading the right files, or from spending more tokens?]");
s.addNotes("75 s. Left: the fair comparison the paper did not run. Right: the ablation isolates the read step. Say whether differences exceed the std across seeds.");

// 7. Published-label check + base rate
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Task 39 check and why κ matters");
[["Agent (ours, 7B)", pct("original|agent_judge|1"), H.amber], ["LLM (ours, 7B)", pct("original|llm_judge|1"), H.slate], ["Paper, agent / LLM", "90.4 / 60.4%", H.teal]].forEach((c, i) => {
  const x = 0.5 + i * 3.07;
  R(s, { x, y: 1.2, w: 2.86, h: 1.6, fill: { color: H.mist } });
  T(s, c[1], { x: x + 0.2, y: 1.35, w: 2.5, h: 0.7, fontSize: 24, bold: true, color: c[2], fontFace: "Cambria", valign: "middle" });
  T(s, c[0], { x: x + 0.2, y: 2.1, w: 2.5, h: 0.5, fontSize: 13 });
});
T(s, `Only ${S ? S.n_requirements.original : 7} requirements on the original workspace: a sanity check, not a result. Paper: GPT-4o, all 55 tasks, black-box.`, { x: 0.5, y: 3.0, w: 9, h: 0.5, fontSize: 13, italic: true });
R(s, { x: 0.5, y: 3.65, w: 9, h: 1.3, fill: { color: H.sand } });
T(s, S ? `${(100 * S.base_rate_satisfied).toFixed(1)}% of requirements are satisfied, so answering "no" every time already scores ${(100 * (1 - S.base_rate_satisfied)).toFixed(1)}% alignment, with κ = 0.` : "[base rate]% of requirements are satisfied, so answering \"no\" every time already scores [100 − base rate]% alignment, with κ = 0.",
  { x: 0.8, y: 3.75, w: 8.4, h: 1.1, fontSize: 16, bold: true, color: H.ink, valign: "middle" });
s.addNotes("45 s. Be honest that 7 requirements cannot confirm the paper. Then explain the base-rate trap from Phase 1 Gap 4.");

// 8. Failure case
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "A failure, read from its trace");
const steps = ["Requirement", "locate returned", "read opened", "verdict said", "cause"];
steps.forEach((st, i) => {
  const y = 1.2 + i * 0.75;
  badge(s, 0.5, y, String(i + 1), i === 4 ? H.red : H.teal, 0.5);
  T(s, st, { x: 1.15, y, w: 2.0, h: 0.5, fontSize: 14, bold: true, color: H.ink, valign: "middle" });
  placeholder(s, 3.2, y - 0.03, 6.3, 0.56, `[from traces/main/agent_judge/seed_*/<task>__R<i>.json]`);
});
s.addNotes("60 s. Pick one entry of results/main/failure_cases.md, open its trace, and fill the five boxes. Show the trace file during the viva if asked.");

// 9. Limitations + four weeks
s = pres.addSlide({ masterName: "CONTENT" });
title(s, "Limitations and four more weeks");
const cols = [["Limitations", H.red, ["One labeller; agreement is with my reading", "Generated workspaces ≠ OpenHands outputs", "One judge model; images unseen (text-only)", "T = 0.7 adds variance at k = 1"]],
  ["Four more weeks", H.teal, ["Second labeller, inter-rater κ", "Second judge family (Phase 1 Gap 3)", "Gray-box: use the saved trajectories", "Ask authors again for the 54 workspaces"]]];
cols.forEach((c, i) => {
  const x = 0.5 + i * 4.6;
  R(s, { x, y: 1.2, w: 4.4, h: 3.2, fill: { color: H.mist } });
  T(s, c[0], { x: x + 0.3, y: 1.4, w: 3.8, h: 0.45, fontSize: 18, bold: true, color: c[1], fontFace: "Cambria" });
  T(s, c[2].map((b, j) => ({ text: b, options: { bullet: true, breakLine: j < c[2].length - 1 } })), { x: x + 0.3, y: 2.0, w: 3.8, h: 2.8, fontSize: 14, paraSpaceAfter: 8 });
});
s.addNotes("45 s. State limitations without being asked; it is graded.");

// 10. Demo
s = pres.addSlide({ masterName: "DARK" });
T(s, "LIVE DEMO", { x: 0.6, y: 0.75, w: 8.8, h: 0.4, fontSize: 14, bold: true, color: H.amber, charSpacing: 2 });
T(s, "One requirement, both judges, every step", { x: 0.6, y: 1.3, w: 8.8, h: 0.9, fontSize: 30, bold: true, color: H.paper, fontFace: "Cambria" });
R(s, { x: 0.6, y: 2.5, w: 8.8, h: 0.8, fill: { color: H.ink2 } });
T(s, "python scripts/demo.py --task 39_Drug_Response_Prediction_SVM_GDSC_ML --req 5", { x: 0.85, y: 2.5, w: 8.4, h: 0.8, fontSize: 13, color: H.sand, fontFace: "Courier New", valign: "middle" });
T(s, "Shows: human label · locate → read → 3 votes for the agent · 3 votes for the LLM judge · tokens used. Backup: a ≤ 3-minute screen recording.", { x: 0.6, y: 3.6, w: 8.8, h: 0.9, fontSize: 15, color: H.ice });
s.addNotes("2 min. Run the demo live; if Ollama is slow, play the recording.");

const out = path.join(__dirname, "RP2_U23AI035_slides.pptx");
pres.writeFile({ fileName: out }).then(() => console.log(`wrote ${out} (${S ? "filled from results" : "draft with placeholders"})`));
