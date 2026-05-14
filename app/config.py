from functools import lru_cache
from pathlib import Path
import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Kayra")
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", "data/knowledge"))
    log_dir: Path = Path(os.getenv("LOG_DIR", "runtime"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.22"))
    top_k: int = int(os.getenv("TOP_K", "4"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
