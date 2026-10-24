"""Turns a developer agent's output folder into text a judge can read.

Two views are provided:
  * `render_tree`      the workspace structure (used by both judges)
  * `read_file`        one file as text (used by the agent judge after `locate`)
  * `dump_workspace`   tree + every readable file, truncated to a token cap
                       (the evidence given to LLM-as-a-Judge, as in the paper's baseline)

Binary artefacts (images, model weights) cannot be shown to a text-only 7B model,
so they are described by type and size. This is a declared deviation from the paper,
whose judge read images with a multimodal model.
"""
from __future__ import annotations

from pathlib import Path

from aaj.tokens import truncate_to_tokens

IGNORE_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "judge", ".venv", "venv", "node_modules", ".aaj"}
TEXT_EXT = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".cfg", ".ini", ".toml", ".html",
            ".js", ".css", ".sh", ".r", ".ipynb", ".log", ".tex", ".xml"}
TABLE_EXT = {".csv", ".tsv"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in IGNORE_DIRS for part in p.relative_to(root).parts):
            yield p


def render_tree(root: Path, max_lines: int = 200) -> str:
    """`tree`-style listing rooted at '/workspace' so paths are stable across machines."""
    lines = ["/workspace"]

    def walk(d: Path, prefix: str):
        entries = sorted([e for e in d.iterdir() if e.name not in IGNORE_DIRS],
                         key=lambda e: (e.is_file(), e.name.lower()))
        for i, e in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{e.name}")
            if e.is_dir():
                walk(e, prefix + ("    " if last else "│   "))

    if root.exists():
        walk(root, "")
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more entries)"]
    return "\n".join(lines)


def to_workspace_path(root: Path, p: Path) -> str:
    return "/workspace/" + p.relative_to(root).as_posix()


def resolve_workspace_path(root: Path, path: str) -> Path | None:
    """Map a path returned by the locate step back to a real file, tolerating /project or /workspace prefixes."""
    rel = path.strip().strip("`'\"").replace("\\", "/")
    for prefix in ("/workspace/", "workspace/", "/project/", "project/", "./", "/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:  # path escapes the workspace
        return None
    if candidate.is_file():
        return candidate
    if candidate.is_dir():  # a folder was located: return it, read_file lists it
        return candidate
    return None


def read_file(p: Path, max_tokens: int, hf_id: str | None) -> str:
    ext = p.suffix.lower()
    try:
        if p.is_dir():
            items = sorted(x.name for x in p.iterdir())
            return f"[directory with {len(items)} entries: {', '.join(items[:30])}]"
        size = p.stat().st_size
        if ext in IMAGE_EXT:
            return _describe_image(p, size)
        if ext == ".pdf":
            return truncate_to_tokens(_pdf_text(p), max_tokens, hf_id)
        if ext in TABLE_EXT:
            with open(p, encoding="utf-8", errors="replace") as f:
                head = [next(f, "") for _ in range(15)]
            return f"[table file, {size} bytes; first rows]\n" + "".join(head)
        if ext in TEXT_EXT or (size < 200_000 and _looks_textual(p)):
            text = p.read_text(encoding="utf-8", errors="replace")
            return truncate_to_tokens(text, max_tokens, hf_id) if text.strip() else "[empty file]"
        return f"[binary file, {ext or 'no extension'}, {size} bytes]"
    except OSError as e:
        return f"[could not read file: {e}]"


def dump_workspace(root: Path, max_tokens: int, hf_id: str | None, max_tree_lines: int = 200,
                   max_file_tokens: int = 2000) -> str:
    """Everything the LLM-as-a-Judge baseline sees: the tree, then each file in path order."""
    parts = [f"Workspace structure:\n{render_tree(root, max_tree_lines)}\n"]
    for p in iter_files(root):
        parts.append(f"Content of {to_workspace_path(root, p)}:\n```\n{read_file(p, max_file_tokens, hf_id)}\n```\n")
    return truncate_to_tokens("\n".join(parts), max_tokens, hf_id)


def _looks_textual(p: Path) -> bool:
    with open(p, "rb") as f:
        chunk = f.read(2048)
    return b"\x00" not in chunk


def _describe_image(p: Path, size: int) -> str:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return f"[image file, {im.format}, {im.width}x{im.height} pixels, {size} bytes; content not viewable by a text-only judge]"
    except Exception:
        return f"[image file, {size} bytes; content not viewable by a text-only judge]"


def _pdf_text(p: Path) -> str:
    try:
        from pypdf import PdfReader
        text = "\n".join((page.extract_text() or "") for page in PdfReader(str(p)).pages)
        return f"[PDF, {len(text)} characters of text]\n{text}" if text.strip() else "[PDF with no extractable text]"
    except Exception as e:
        return f"[PDF that could not be parsed: {e}]"
