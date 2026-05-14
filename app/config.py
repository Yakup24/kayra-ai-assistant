from functools import lru_cache
from pathlib import Path
import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Kayra")
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", "data/knowledge"))
    log_dir: Path = Path(os.getenv("LOG_DIR", "runtime"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.22"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    auth_secret: str = os.getenv("AUTH_SECRET", "change-this-kayra-dev-secret")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "KayraAdmin2026!")


@lru_cache
def get_settings() -> Settings:
    return Settings()
