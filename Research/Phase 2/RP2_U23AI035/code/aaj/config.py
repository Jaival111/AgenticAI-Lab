"""Loads the pinned experiment configuration and resolves repository paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
TRACES = ROOT / "traces"


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else ROOT / "configs" / "experiment.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["ollama"]["host"] = os.environ.get("OLLAMA_HOST", cfg["ollama"]["host"]).rstrip("/")
    if not cfg["ollama"]["host"].startswith("http"):
        cfg["ollama"]["host"] = "http://" + cfg["ollama"]["host"]
    cfg["_path"] = str(path)
    return cfg


def load_prompt(name: str) -> str:
    """Prompts live in prompts/*.txt so that they are versioned artefacts, never edited in code."""
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8")


def devai_dir(cfg: dict) -> Path:
    return ROOT / cfg["devai"]["local_dir"]
