# CarePulse-AI

Health information assistant: chat LLM + RAG + symptom-based condition predictor, wrapped in safety guardrails.
**Not a medical device. Outputs are informational only.**

## Layout
| Path | Purpose |
|---|---|
| `app/api` | FastAPI routes (`/chat`, `/predict`) |
| `app/schemas` | Pydantic request/response models |
| `app/core` | Settings + PII-redacting logging |
| `app/llm` | Model, tokenizer, generation, checkpoints |
| `app/conversation` | Orchestration (guardrails -> RAG -> LLM -> guardrails) and session memory |
| `app/disease` | Symptom -> possible-conditions predictor |
| `app/rag` | Retriever + vector store over `data/knowledge_base` |
| `app/safety` | Emergency detection, dosage/diagnosis blocking, disclaimers |
| `scripts` | `train.py`, `evaluate.py`, `train_disease.py` |

## Quickstart
```bash
cp .env.example .env
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```
The API boots without models: `/chat` falls back to RAG-only answers and `/predict` returns 503.

## Models
Artifacts (`*.pt`, `*.pkl`) are git-ignored. Store them in Git LFS or object storage and mount them (see `docker-compose.yml`).
```bash
python scripts/train.py --data data/processed/corpus.txt
python scripts/train_disease.py --csv data/raw/symptoms.csv
```

## Roadmap / recommendations
- Fine-tune an open model (LoRA) instead of from-scratch training for medical accuracy; keep RAG for facts.
- Replace TF-IDF with embeddings + Chroma/Qdrant.
- Move session memory to Redis with encryption; add consent + data-deletion flow (`DELETE /chat/{id}` exists).
- Clinician review of guardrail rules and knowledge base before any real users.
