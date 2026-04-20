from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    openai_api_key: str
    openai_org_id: str = ""

    orchestrator_model: str = "gpt-4o"
    agent_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    chroma_persist_dir: str = ".chroma"
    rag_top_k: int = 5
    rag_score_threshold: float = 0.75

    critic_pass_threshold: float = 0.70
    max_revision_cycles: int = 2

    sqlite_db_path: str = ".state/checkpoints.db"

    company_name: str = "Verdant Intelligence"
    company_domain: str = "energy_benchmarking_compliance"

    class Config:
        env_file = ".env"


settings = Settings()
