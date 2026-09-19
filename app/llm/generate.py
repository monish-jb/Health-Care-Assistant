import logging
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.llm.tokenizer import ByteTokenizer

log = logging.getLogger(__name__)


def generate(model, tokenizer, prompt: str, max_new_tokens=200, temperature=0.7, top_k=40, device="cpu") -> str:
    import torch
    ids = tokenizer.encode(prompt)
    x = torch.tensor([ids], dtype=torch.long, device=device)
    with torch.no_grad():
        for _ in range(max_new_tokens):
            logits, _ = model(x[:, -model.config.block_size:])
            logits = logits[:, -1, :] / max(temperature, 1e-5)
            if top_k:
                v, _ = torch.topk(logits, top_k)
                logits[logits < v[:, [-1]]] = -float("inf")
            nxt = torch.multinomial(torch.softmax(logits, dim=-1), 1)
            x = torch.cat([x, nxt], dim=1)
    return tokenizer.decode(x[0, len(ids):].tolist())


class Engine:
    def __init__(self, model, tokenizer):
        self.model, self.tokenizer = model, tokenizer

    def complete(self, prompt: str) -> str:
        s = get_settings()
        return generate(self.model, self.tokenizer, prompt, s.max_new_tokens, s.temperature)


@lru_cache
def get_engine() -> Engine | None:
    """Returns None if no checkpoint exists so the API still boots (RAG-only fallback)."""
    path = get_settings().llm_checkpoint
    if not Path(path).exists():
        log.warning("LLM checkpoint not found at %s; running without generation", path)
        return None
    from app.llm.checkpoint import load_checkpoint
    return Engine(load_checkpoint(path), ByteTokenizer())
