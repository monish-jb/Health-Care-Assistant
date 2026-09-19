from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _chunk(text: str, size: int = 600) -> list[str]:
    paras, chunks, cur = [p.strip() for p in text.split("\n\n") if p.strip()], [], ""
    for p in paras:
        if len(cur) + len(p) > size and cur:
            chunks.append(cur.strip())
            cur = ""
        cur += p + "\n\n"
    return chunks + ([cur.strip()] if cur.strip() else [])


class VectorStore:
    """TF-IDF store (no external service). Swap for Chroma/Qdrant + embeddings later."""

    def __init__(self, directory: str):
        self.docs: list[tuple[str, str]] = []  # (source, chunk)
        for f in sorted(Path(directory).glob("**/*")):
            if f.suffix in {".md", ".txt"}:
                self.docs += [(f.name, c) for c in _chunk(f.read_text(encoding="utf-8"))]
        self.vec = TfidfVectorizer(stop_words="english")
        self.matrix = self.vec.fit_transform([c for _, c in self.docs]) if self.docs else None

    def search(self, query: str, k: int = 3, min_score: float = 0.1):
        if self.matrix is None:
            return []
        scores = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        top = scores.argsort()[::-1][:k]
        return [(self.docs[i][0], self.docs[i][1], float(scores[i])) for i in top if scores[i] >= min_score]
