"""Run the local developer agent on every task in the subset to create workspaces to judge.

  python scripts/02_generate_workspaces.py                      # write files only (safe default)
  python scripts/02_generate_workspaces.py --i-understand-exec-risk   # also run code (use Docker!)

Inside the Docker sandbox (docker/Dockerfile.devagent) AAJ_SANDBOX=1 enables execution.
Existing workspaces are skipped, so the script can be resumed after an interruption.
"""
import argparse
import json
import os
import shutil
import time

import _bootstrap  # noqa: F401
from aaj.config import load_config, devai_dir
from aaj.data import generated_trajectory, generated_workspace, load_instance, load_subset
from aaj.devagent import run_developer, save_trajectory
from aaj.llm import LLMError, OllamaChat

ap = argparse.ArgumentParser()
ap.add_argument("--i-understand-exec-risk", action="store_true",
                help="let the developer agent execute shell commands on this machine")
ap.add_argument("--tasks", nargs="*", help="only these task names")
ap.add_argument("--redo", action="store_true", help="regenerate workspaces that already exist")
args = ap.parse_args()

cfg = load_config()
d = cfg["developer"]
allow_exec = args.i_understand_exec_risk or os.environ.get("AAJ_SANDBOX") == "1"
print(f"developer model: {d['model']}   command execution: {'ON' if allow_exec else 'OFF (write-only)'}")
constraints = json.loads((devai_dir(cfg) / "benchmark" / "devai" / "constraints.json").read_text(encoding="utf-8"))
llm = OllamaChat(cfg["ollama"]["host"], d["model"], temperature=d["temperature"], top_p=d["top_p"],
                 num_ctx=d["num_ctx"], num_predict=d["num_predict"],
                 timeout_s=cfg["ollama"]["request_timeout_s"], max_retries=cfg["ollama"]["max_retries"])
tasks = args.tasks or load_subset(cfg)
log_path = generated_trajectory(cfg, "_generation_log").with_name("_generation_log.json")
log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {"tasks": {}}
log.update({"developer": d, "exec_enabled": allow_exec, "model_info": llm.model_info()})
for t in tasks:
    ws = generated_workspace(cfg, t)
    if ws.exists() and any(ws.iterdir()) and not args.redo:
        print(f"[skip] {t} already has a workspace")
        continue
    if ws.exists():
        shutil.rmtree(ws)
    print(f"[task] {t}")
    t0 = time.perf_counter()
    try:
        traj = run_developer(load_instance(cfg, t), constraints, ws, llm, d, allow_exec)
        status = "ok"
    except LLMError as e:  # keep going: a failed task simply yields a sparse workspace
        traj, status = [], f"llm_error: {e}"
        print(f"  !! {status}")
    save_trajectory(traj, generated_trajectory(cfg, t))
    log["tasks"][t] = {"status": status, "steps": len(traj), "wall_s": time.perf_counter() - t0,
                       "input_tokens": sum(s["step_usage"]["input_tokens"] for s in traj),
                       "output_tokens": sum(s["step_usage"]["output_tokens"] for s in traj)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")  # saved after every task
print(f"done; log -> {log_path}")
