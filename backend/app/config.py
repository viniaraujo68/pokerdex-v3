from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="POKERDEX_", extra="ignore")

    # Where the SQLite file lives. In Docker this points at the mounted volume.
    database_url: str = "sqlite:///./pokerdex.db"

    # Session / cookie
    session_cookie_name: str = "pokerdex_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # set true in production (HTTPS via Caddy)
    cookie_samesite: str = "lax"

    # Comma-separated origins allowed in dev (prod is same-origin behind Caddy → none needed)
    cors_origins: str = "http://localhost:5173"


settings = Settings()
