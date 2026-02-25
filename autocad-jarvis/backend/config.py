"""Application settings loaded from environment variables via Pydantic BaseSettings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration sourced from .env file and environment variables."""

    # OpenRouter (primary — Gemini 2.5 Pro)
    openrouter_api_key: str = ""
    ai_model: str = "google/gemini-2.5-pro"
    ai_fast_model: str = "google/gemini-2.5-flash"
    ai_base_url: str = "https://openrouter.ai/api/v1"

    # OpenAI fallback
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    openai_reasoning_model: str = "o3"
    openai_mini_model: str = "gpt-5-mini"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8765
    log_level: str = "INFO"
    watch_paths: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def watch_paths_list(self) -> list[str]:
        """Return list of directories to watch, with ~ expansion."""
        if not self.watch_paths:
            return [
                str(Path.home() / "Desktop"),
                str(Path.home() / "Documents"),
            ]
        return [
            str(Path(p.strip()).expanduser())
            for p in self.watch_paths.split(",")
            if p.strip()
        ]


settings = Settings()
