import logging

from app.conversation.memory import memory
from app.llm.generate import get_engine
from app.rag.retriever import retrieve
from app.safety import guardrails

log = logging.getLogger(__name__)

SYSTEM = ("You are CarePulse, a careful health information assistant. Give general, "
          "educational information only. Never diagnose or give medication doses.")


def _build_prompt(sid: str, message: str, docs: list[dict]) -> str:
    ctx = "\n".join(f"- {d['text'][:400]}" for d in docs)
    hist = "\n".join(f"{r}: {t}" for r, t in memory.history(sid))
    return f"System: {SYSTEM}\nContext:\n{ctx}\n{hist}\nUser: {message}\nAssistant:"


def respond(sid: str, message: str) -> dict:
    # 1) Pre-LLM safety
    check = guardrails.check_input(message)
    if check.emergency:
        log.warning("emergency path triggered")
        return {"reply": check.message, "emergency": True, "sources": []}

    # 2) Retrieve + generate
    docs = retrieve(message)
    engine = get_engine()
    if engine:
        raw = engine.complete(_build_prompt(sid, message, docs))
        raw = raw.split("\nUser:")[0].split("\nSystem:")[0]
    elif docs:  # fallback: RAG-only answer when no model is loaded
        raw = "Here is what I found in my reference material:\n" + docs[0]["text"]
    else:
        raw = "I don't have enough information to help with that yet."

    # 3) Post-LLM safety
    reply = guardrails.check_output(raw)
    memory.add(sid, "User", message)
    memory.add(sid, "Assistant", reply)
    return {"reply": reply, "emergency": False, "sources": sorted({d["source"] for d in docs})}
