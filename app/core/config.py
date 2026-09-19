from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    llm_checkpoint: str = "checkpoints/carepulse_llm.pt"
    disease_model_path: str = "app/disease/model.pkl"
    knowledge_base_dir: str = "data/knowledge_base"
    max_new_tokens: int = 200
    temperature: float = 0.7
    session_ttl_seconds: int = 1800
    max_history_turns: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
