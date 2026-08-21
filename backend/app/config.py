import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./health_navigator.db"
    SECRET_KEY: str = "super-secret-key-change-in-production-32-chars-minimum"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    LLM_PROVIDER: str = "template"  # template | ollama | anthropic | openai | gemini
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""

    RAG_CONFIDENCE_THRESHOLD: float = 0.15

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
