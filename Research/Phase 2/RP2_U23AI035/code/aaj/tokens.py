"""Exact prompt-token counting with the judge model's Hugging Face tokenizer.

Only the tokenizer file is downloaded (a few MB), never the model weights.
If the download is impossible (offline), we fall back to a 4-characters-per-token
estimate and say so in the manifest via `tokenizer_status()`.
"""
from __future__ import annotations

from functools import lru_cache

_STATUS = {"mode": "unloaded"}
# Qwen2.5 chat template adds <|im_start|>role\n ... <|im_end|>\n around each message,
# plus <|im_start|>assistant\n for the generation prompt.
_PER_MESSAGE_OVERHEAD = 5
_GENERATION_PROMPT = 3


@lru_cache(maxsize=4)
def _load(hf_id: str):
    try:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_pretrained(hf_id)
        _STATUS.update(mode="hf_tokenizer", hf_id=hf_id)
        return tok
    except Exception as e:  # offline or package missing
        _STATUS.update(mode="char_estimate", error=str(e))
        return None


def count_text_tokens(text: str, hf_id: str | None) -> int:
    tok = _load(hf_id) if hf_id else None
    if tok is None:
        return max(1, len(text) // 4)
    return len(tok.encode(text, add_special_tokens=False).ids)


def count_chat_tokens(messages: list[dict], hf_id: str | None) -> int:
    return sum(count_text_tokens(m["content"], hf_id) + _PER_MESSAGE_OVERHEAD for m in messages) + _GENERATION_PROMPT


def truncate_to_tokens(text: str, max_tokens: int, hf_id: str | None) -> str:
    """Keep the head of `text` within `max_tokens`; mark the cut so the judge knows."""
    if count_text_tokens(text, hf_id) <= max_tokens:
        return text
    tok = _load(hf_id) if hf_id else None
    if tok is None:
        cut = text[: max_tokens * 4]
    else:
        ids = tok.encode(text, add_special_tokens=False).ids[:max_tokens]
        cut = tok.decode(ids)
    return cut + "\n...[truncated]..."


def tokenizer_status() -> dict:
    return dict(_STATUS)
