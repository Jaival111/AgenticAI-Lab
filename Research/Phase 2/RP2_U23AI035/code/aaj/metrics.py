"""Agreement and cost metrics, computed offline from the saved per-sample records.

A record (one line of results/<run_id>/<judge>/seed_<s>.jsonl) holds, for one requirement,
the ground-truth label and every sample drawn. `vote(record, k)` gives the k-sample
majority verdict and `cost(record, k)` the calls/tokens/latency that k samples would cost,
so any k <= k_max can be evaluated without calling the model again.
"""
from __future__ import annotations

import math
from statistics import mean, stdev


def verdict_samples(record: dict) -> list[dict]:
    return [s for s in record["steps"] if s["step"] == "judge"]


def vote(record: dict, k: int) -> bool:
    """Majority over the first k verdicts. An unparsable sample counts as UNSATISFIED
    (a judge that does not answer has not confirmed the requirement); ties -> UNSATISFIED."""
    vs = [bool(s["verdict"]) for s in verdict_samples(record)[:k]]
    return sum(vs) > len(vs) / 2


def cost(record: dict, k: int) -> dict:
    """Cost of producing the k-sample verdict: all non-judge calls + the first k judge calls."""
    calls = [s for s in record["steps"] if s["step"] not in ("judge", "read")]
    calls += verdict_samples(record)[:k]
    return {"calls": len(calls),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens": sum(c["completion_tokens"] for c in calls),
            "latency_s": sum(c["latency_s"] for c in calls)}


def unparsed_rate(records: list[dict], k: int) -> float:
    vs = [s for r in records for s in verdict_samples(r)[:k]]
    return sum(s["verdict"] is None for s in vs) / max(1, len(vs))


def confusion(y_true: list[bool], y_pred: list[bool]) -> dict:
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def alignment(y_true, y_pred) -> float:
    """The paper's Alignment Rate: share of requirements where judge == human."""
    return sum(t == p for t, p in zip(y_true, y_pred)) / max(1, len(y_true))


def cohen_kappa(y_true, y_pred) -> float:
    """Chance-corrected agreement (addresses Gap 4: raw alignment flatters a judge that says 'no')."""
    n = len(y_true)
    if n == 0:
        return float("nan")
    po = alignment(y_true, y_pred)
    p_true = sum(y_true) / n
    p_pred = sum(y_pred) / n
    pe = p_true * p_pred + (1 - p_true) * (1 - p_pred)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def f1_positive(y_true, y_pred) -> float:
    c = confusion(y_true, y_pred)
    denom = 2 * c["tp"] + c["fp"] + c["fn"]
    return 2 * c["tp"] / denom if denom else float("nan")


def score_run(records: list[dict], k: int) -> dict:
    y = [r["label"] for r in records]
    p = [vote(r, k) for r in records]
    costs = [cost(r, k) for r in records]
    n = max(1, len(records))
    return {"n": len(records), "alignment": alignment(y, p), "kappa": cohen_kappa(y, p),
            "f1_pos": f1_positive(y, p), "unparsed": unparsed_rate(records, k),
            "calls_per_req": sum(c["calls"] for c in costs) / n,
            "prompt_tok_per_req": sum(c["prompt_tokens"] for c in costs) / n,
            "completion_tok_per_req": sum(c["completion_tokens"] for c in costs) / n,
            "tokens_per_req": sum(c["prompt_tokens"] + c["completion_tokens"] for c in costs) / n,
            "latency_s_per_req": sum(c["latency_s"] for c in costs) / n,
            **confusion(y, p)}


def mean_std(values: list[float]) -> tuple[float, float]:
    vals = [v for v in values if not (isinstance(v, float) and math.isnan(v))]
    if not vals:
        return float("nan"), float("nan")
    return mean(vals), (stdev(vals) if len(vals) > 1 else 0.0)


def aggregate(per_seed: list[dict]) -> dict:
    """Mean and sample standard deviation over repeated runs for every numeric field."""
    out = {}
    for key in per_seed[0]:
        if isinstance(per_seed[0][key], (int, float)):
            m, s = mean_std([d[key] for d in per_seed])
            out[key] = m
            out[key + "_std"] = s
    out["n_runs"] = len(per_seed)
    return out


def matched_k(tokens_by_k: dict[int, float], target_tokens: float) -> int:
    """The k whose mean tokens/requirement is closest to the target budget."""
    return min(tokens_by_k, key=lambda k: abs(tokens_by_k[k] - target_tokens))


__all__ = ["vote", "cost", "score_run", "aggregate", "matched_k", "cohen_kappa", "alignment",
           "f1_positive", "confusion", "mean_std"]
