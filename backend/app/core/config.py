from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Load backend/.env when running from the backend directory.
# Existing environment variables take precedence.
load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _maira_base_url() -> str:
    """Return the provider host without the ask endpoint."""
    base = os.getenv(
        "MAIRA_BASE_URL",
        "https://api.recommender.gigalogy.com",
    ).strip().rstrip("/")

    ask_suffix = "/v1/maira/ask"

    if base.endswith(ask_suffix):
        base = base[:-len(ask_suffix)].rstrip("/")

    return base


def _maira_ask_url() -> str:
    """Use the configured ask URL or append the route exactly once."""
    explicit = os.getenv("MAIRA_ASK_URL", "").strip().rstrip("/")

    if explicit:
        return explicit

    return f"{_maira_base_url()}/v1/maira/ask"


def _default_local_dataset_path() -> str:
    """Resolve the local dataset from the project root."""
    project_root = Path(__file__).resolve().parents[3]

    return str(
        project_root
        / "data"
        / "maira"
        / "National_Land_Integrity_Maira_All_Data_One_JSON_ASCII_UTF8_CORRECTED.json"
    )


@dataclass
class Settings:
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/land_integrity",
    )

    # JWT authentication
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "local-development-secret-change-me",
    )
    jwt_access_minutes: int = int(
        os.getenv("JWT_ACCESS_MINUTES", "30")
    )
    jwt_refresh_days: int = int(
        os.getenv("JWT_REFRESH_DAYS", "7")
    )

    # Cookie security
    cookie_secure: bool = env_bool("COOKIE_SECURE", False)
    cookie_samesite: str = os.getenv(
        "COOKIE_SAMESITE",
        "Lax",
    )
    jwt_cookie_csrf_protect: bool = env_bool(
        "JWT_COOKIE_CSRF_PROTECT",
        True,
    )

    # CORS
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8080,http://localhost:5173",
        ).split(",")
        if item.strip()
    )

    app_env: str = os.getenv(
        "APP_ENV",
        "development",
    )

    # Maira service-to-service configuration
    maira_enabled: bool = env_bool(
        "MAIRA_ENABLED",
        False,
    )

    maira_base_url: str = _maira_base_url()
    maira_ask_url: str = _maira_ask_url()

    maira_api_key: str = os.getenv(
        "MAIRA_API_KEY",
        "",
    ).strip()

    maira_project_key: str = os.getenv(
        "MAIRA_PROJECT_KEY",
        "",
    ).strip()

    # Maira request identifiers; these are not login credentials.
    maira_user_id: str = os.getenv(
        "MAIRA_USER_ID",
        "national-land-integrity-chatbot-service",
    ).strip()

    maira_member_id: str = os.getenv(
        "MAIRA_MEMBER_ID",
        "",
    ).strip()

    # Explicit GPT profile selection
    maira_gpt_profile_id: str = os.getenv(
        "MAIRA_GPT_PROFILE_ID",
        "",
    ).strip()

    # Optional dataset filtering
    maira_dataset_id: str = os.getenv(
        "MAIRA_DATASET_ID",
        "",
    ).strip()

    # Local synthetic Land ID dataset path
    # Fixes the missing maira_local_dataset_path attribute.
    maira_local_dataset_path: str = os.getenv(
        "MAIRA_LOCAL_DATASET_PATH",
        _default_local_dataset_path(),
    ).strip()

    # Provider timeout
    maira_timeout_seconds: float = float(
        os.getenv("MAIRA_TIMEOUT_SECONDS", "90")
    )

    # Upload configuration
    upload_dir: str = os.getenv(
        "UPLOAD_DIR",
        "storage/uploads",
    )

    max_upload_mb: int = int(
        os.getenv("MAX_UPLOAD_MB", "15")
    )

    # Platform pagination, bootstrap and private object storage
    pagination_size: int = int(os.getenv("PAGINATION_SIZE", "10"))
    admin_seed_email: str = os.getenv("ADMIN_SEED_EMAIL", "")
    admin_seed_password: str = os.getenv("ADMIN_SEED_PASSWORD", "")
    admin_seed_name: str = os.getenv("ADMIN_SEED_NAME", "System Administrator")
    documents_max_per_user: int = int(os.getenv("DOCUMENTS_MAX_PER_USER", "50"))
    s3_bucket: str = os.getenv("S3_BUCKET", "nli-user-documents")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
    s3_access_key_id: str = os.getenv("S3_ACCESS_KEY_ID", "")
    s3_secret_access_key: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
    s3_presign_expires_seconds: int = int(os.getenv("S3_PRESIGN_EXPIRES_SECONDS", "300"))

    # Chat caching
    chat_cache_ttl_seconds: int = int(os.getenv("CHAT_CACHE_TTL_SECONDS", "60"))


settings = Settings()