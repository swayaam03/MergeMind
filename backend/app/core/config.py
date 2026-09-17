from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate root directory (MergeMind/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub App Configuration
    GITHUB_APP_SLUG: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_PRIVATE_KEY_PATH: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # Application URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # Repository Context Limits
    MERGEMIND_MAX_DOCUMENTATION_CHARS: int = 10_000
    MERGEMIND_MAX_TREE_ENTRIES: int = 500
    MERGEMIND_MAX_RELEVANT_FILES: int = 10

    # LLM Merge Agent Configuration (LiteLLM / OpenRouter)
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 60
    MERGEMIND_RUN_LLM_INTEGRATION_TESTS: bool = False

    @property
    def github_installation_url(self) -> str:
        """Construct the GitHub App installation URL."""
        if not self.GITHUB_APP_SLUG or not self.GITHUB_APP_SLUG.strip():
            return ""
        return f"https://github.com/apps/{self.GITHUB_APP_SLUG.strip()}/installations/new"


settings = Settings()
