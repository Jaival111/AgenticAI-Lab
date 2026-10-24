import math

from aaj.metrics import alignment, cohen_kappa, cost, f1_positive, matched_k, vote


def rec(verdicts, label=True, prompt=100):
    steps = [{"step": "locate", "prompt_tokens": 50, "completion_tokens": 10, "latency_s": 1.0},
             {"step": "read"}]
    steps += [{"step": "judge", "verdict": v, "prompt_tokens": prompt, "completion_tokens": 20, "latency_s": 2.0}
              for v in verdicts]
    return {"label": label, "steps": steps}


def test_vote_majority_and_ties():
    r = rec([True, False, True, None, False])
    assert vote(r, 1) is True
    assert vote(r, 2) is False          # tie -> unsatisfied
    assert vote(r, 3) is True
    assert vote(r, 5) is False          # None counts as unsatisfied: 2 of 5


def test_cost_counts_locate_once_and_k_verdicts():
    c = cost(rec([True] * 5), 3)
    assert c["calls"] == 4 and c["prompt_tokens"] == 50 + 300 and c["completion_tokens"] == 10 + 60


def test_kappa_zero_for_constant_judge():
    y = [True, False, False, False]
    assert alignment(y, [False] * 4) == 0.75
    assert cohen_kappa(y, [False] * 4) == 0.0
    assert cohen_kappa(y, y) == 1.0


def test_f1_nan_without_positives():
    assert math.isnan(f1_positive([False, False], [False, False]))


def test_matched_k():
    assert matched_k({1: 3000, 3: 9000, 5: 15000}, 8000) == 3
