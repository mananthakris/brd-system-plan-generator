from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    openai_api_key: str
    openai_org_id: str = ""

    orchestrator_model: str = "gpt-5.4"
    agent_model: str = "gpt-5.4"
    fast_model: str = "gpt-5.4-mini"
    embedding_model: str = "text-embedding-3-small"

    chroma_persist_dir: str = ".chroma"
    rag_top_k: int = 5
    rag_score_threshold: float = 0.75

    critic_pass_threshold: float = 0.70
    max_revision_cycles: int = 2

    sqlite_db_path: str = ".state/checkpoints.db"

    company_name: str = "Arbor Risk"
    company_domain: str = "lending_fraud_detection"

    class Config:
        env_file = ".env"


settings = Settings()
