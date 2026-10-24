"""Thin Ollama chat client that records cost and latency for every call.

Each call returns an LLMResult with the text, the token counts and the wall-clock
time. Prompt tokens are counted with the model's own tokenizer (aaj.tokens) because
Ollama's `prompt_eval_count` excludes tokens served from its prompt cache, which would
make repeated samples look artificially cheap. Ollama's raw counts are kept as well.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

import requests

from aaj.tokens import count_chat_tokens


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    seed: int
    prompt_tokens: int          # counted with the HF tokenizer (what an API would bill)
    completion_tokens: int      # Ollama eval_count (never cached)
    ollama_prompt_eval_count: int
    latency_s: float
    options: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class OllamaChat:
    def __init__(self, host: str, model: str, *, temperature: float, top_p: float,
                 num_ctx: int, num_predict: int, timeout_s: int = 600, max_retries: int = 3,
                 tokenizer_hf_id: str | None = None):
        self.host = host
        self.model = model
        self.base_options = {"temperature": temperature, "top_p": top_p,
                             "num_ctx": num_ctx, "num_predict": num_predict}
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.tokenizer_hf_id = tokenizer_hf_id

    def chat(self, messages: list[dict], seed: int) -> LLMResult:
        options = dict(self.base_options, seed=seed)
        payload = {"model": self.model, "messages": messages, "stream": False, "options": options}
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                r = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout_s)
                r.raise_for_status()
                data = r.json()
                latency = time.perf_counter() - t0
                text = data.get("message", {}).get("content", "")
                prompt_tokens = (count_chat_tokens(messages, self.tokenizer_hf_id)
                                 if self.tokenizer_hf_id else data.get("prompt_eval_count", 0))
                return LLMResult(text=text, model=self.model, seed=seed,
                                 prompt_tokens=prompt_tokens,
                                 completion_tokens=data.get("eval_count", 0),
                                 ollama_prompt_eval_count=data.get("prompt_eval_count", 0),
                                 latency_s=latency, options=options)
            except (requests.RequestException, ValueError) as e:  # network error or bad JSON
                last_err = e
                time.sleep(2 * attempt)
        raise LLMError(f"Ollama call failed after {self.max_retries} attempts: {last_err}")

    def model_info(self) -> dict:
        """Digest and details of the pinned model, written into every run manifest."""
        r = requests.post(f"{self.host}/api/show", json={"model": self.model}, timeout=60)
        r.raise_for_status()
        info = r.json()
        tags = requests.get(f"{self.host}/api/tags", timeout=60).json().get("models", [])
        digest = next((m.get("digest") for m in tags if m.get("name") == self.model
                       or m.get("model") == self.model), None)
        return {"model": self.model, "digest": digest, "details": info.get("details", {}),
                "modified_at": info.get("modified_at")}
