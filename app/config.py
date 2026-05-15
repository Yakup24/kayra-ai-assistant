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
    token_ttl_hours: int = int(os.getenv("TOKEN_TTL_HOURS", "12"))
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "KayraAdmin2026!")
    support_username: str = os.getenv("SUPPORT_USERNAME", "support")
    support_password: str = os.getenv("SUPPORT_PASSWORD", "KayraSupport2026!")
    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://127.0.0.1:8000,http://127.0.0.1:8001,http://localhost:8000,http://localhost:8001",
        ).split(",")
        if origin.strip()
    ]
    login_rate_limit: int = int(os.getenv("LOGIN_RATE_LIMIT", "60"))
    api_rate_limit: int = int(os.getenv("API_RATE_LIMIT", "180"))
    ticket_rate_limit: int = int(os.getenv("TICKET_RATE_LIMIT", "90"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
