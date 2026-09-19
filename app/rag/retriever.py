from functools import lru_cache

from app.core.config import get_settings
from app.rag.vector_store import VectorStore


@lru_cache
def _store() -> VectorStore:
    return VectorStore(get_settings().knowledge_base_dir)


def retrieve(query: str, k: int = 3) -> list[dict]:
    return [{"source": s, "text": t, "score": sc} for s, t, sc in _store().search(query, k)]
