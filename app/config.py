"""Settings, loaded from environment variables (and .env if present)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("PW_MODE", "mock").lower()
    host: str = os.getenv("PW_HOST", "192.168.91.1")
    gw_password: str = os.getenv("PW_GW_PASSWORD", "")
    timezone: str = os.getenv("PW_TIMEZONE", "America/New_York")
    poll_seconds: int = int(os.getenv("POLL_SECONDS", "5"))
    db_path: str = os.getenv("DB_PATH", "data/powerwall.db")
    web_host: str = os.getenv("WEB_HOST", "0.0.0.0")
    web_port: int = int(os.getenv("WEB_PORT", "8080"))


settings = Settings()
