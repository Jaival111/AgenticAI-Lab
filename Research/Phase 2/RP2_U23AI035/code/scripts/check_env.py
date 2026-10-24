"""Pre-flight check: Ollama reachable, both models pulled, tokenizer downloadable, data present."""
import requests

import _bootstrap  # noqa: F401
from aaj.config import DATA, load_config, devai_dir
from aaj.tokens import count_text_tokens, tokenizer_status

cfg = load_config()
ok = True
try:
    tags = {m["name"] for m in requests.get(f"{cfg['ollama']['host']}/api/tags", timeout=10).json()["models"]}
    print(f"[ok] Ollama at {cfg['ollama']['host']}")
    for role in ("judge", "developer"):
        m = cfg[role]["model"]
        present = m in tags or f"{m}:latest" in tags
        ok &= present
        print(f"[{'ok' if present else 'MISSING'}] {role} model {m}" + ("" if present else f"  -> run: ollama pull {m}"))
except requests.RequestException as e:
    ok = False
    print(f"[FAIL] cannot reach Ollama at {cfg['ollama']['host']}: {e}  -> start the Ollama app or `ollama serve`")
count_text_tokens("hello world", cfg["judge"]["tokenizer_hf_id"])
st = tokenizer_status()
print(f"[{'ok' if st['mode'] == 'hf_tokenizer' else 'WARN'}] token counting mode: {st}")
print(f"[{'ok' if (devai_dir(cfg) / 'benchmark').exists() else 'TODO'}] DevAI repo (scripts/00_fetch_devai.py)")
print(f"[{'ok' if (DATA / 'task_subset.json').exists() else 'TODO'}] task subset (scripts/01_select_tasks.py)")
raise SystemExit(0 if ok else 1)
