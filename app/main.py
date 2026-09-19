from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import chat, prediction
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.llm.generate import get_engine
from app.rag.retriever import _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings().log_level)
    _store()       # warm the RAG index
    get_engine()   # load the LLM once at startup
    yield


app = FastAPI(title="CarePulse-AI", version="0.1.0", lifespan=lifespan)
app.include_router(chat.router)
app.include_router(prediction.router)


@app.get("/health")
def health():
    return {"status": "ok", "llm_loaded": get_engine() is not None}
