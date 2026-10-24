"""Clone the DevAI / Agent-as-a-Judge repository at the pinned commit into data/devai_repo.

Gives us: the 55 task instances, the human-consensus labels for all three developer agents,
and the single released OpenHands workspace (task 39).
"""
import subprocess

import _bootstrap  # noqa: F401
from aaj.config import load_config, devai_dir

cfg = load_config()
dest = devai_dir(cfg)
commit = cfg["devai"]["commit"]
if not (dest / ".git").exists():
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", cfg["devai"]["repo"], str(dest)], check=True)
subprocess.run(["git", "-C", str(dest), "fetch", "--all", "--quiet"], check=True)
subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", commit], check=True)
head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
n_inst = len(list((dest / "benchmark" / "devai" / "instances").glob("*.json")))
ws39 = dest / "benchmark" / "workspaces" / "OpenHands" / "39_Drug_Response_Prediction_SVM_GDSC_ML"
print(f"DevAI repo at {head}  (expected {commit})")
print(f"instances: {n_inst} (expected 55); task-39 workspace present: {ws39.exists()}")
assert head == commit, "checked-out commit differs from the pinned one"
