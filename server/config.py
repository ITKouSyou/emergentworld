from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 主 LLM
    llm_api_key: str = "sk-test"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # 嵌入模型（可留空，留空则记忆检索降级为时间排序）
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    db_path: Path = Path("data/world.db")
    cache_dir: Path = Path(".cache/llm")
    seed: int = 42
    log_level: str = "INFO"

    content_dir: Path = Path("content")

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_api_key.strip())


settings = Settings()
