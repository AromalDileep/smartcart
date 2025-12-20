import os
from pathlib import Path
from dotenv import load_dotenv

# Prioritize .env.local if it exists (local development)
# Fallback to .env (cloud/production or if .env.local is missing)
env_path = Path(".env.local")
if env_path.exists():
    _ = load_dotenv(dotenv_path=env_path, override=True)
else:
    _ = load_dotenv()


class Settings:
    """
    Central config loader — NO fallback secrets.
    Every configuration value MUST be provided in the `.env` file.
    If any required variable is missing, the application should fail early.
    """

    # --------------------------
    # Database
    # --------------------------
    POSTGRES_HOST: str = os.environ["POSTGRES_HOST"]
    POSTGRES_PORT: str = os.environ["POSTGRES_PORT"]
    POSTGRES_USER: str = os.environ["POSTGRES_USER"]
    POSTGRES_PASSWORD: str = os.environ["POSTGRES_PASSWORD"]
    POSTGRES_DB: str = os.environ["POSTGRES_DB"]
    DB_RETRIES: int = int(os.environ["DB_RETRIES"])
    DB_RETRY_DELAY: int = int(os.environ["DB_RETRY_DELAY"])

    # --------------------------
    # FAISS
    # --------------------------
    FAISS_INDEX_DIR: str = os.environ["FAISS_INDEX_DIR"]
    FAISS_DIM: int = int(os.environ["FAISS_DIM"])

    # --------------------------
    # File Paths
    # --------------------------
    IMAGE_DIR: str = os.environ["IMAGE_DIR"]
    STATIC_DIR: str = os.environ["STATIC_DIR"]
    MODEL_PATH: str = os.environ["MODEL_PATH"]
    TEMP_IMAGE_PATH: str = os.environ["TEMP_IMAGE_PATH"]
    TEMP_HYBRID_IMAGE_PATH: str = os.environ["TEMP_HYBRID_IMAGE_PATH"]

    # --------------------------
    # Admin
    # --------------------------
    ADMIN_EMAIL: str = os.environ["ADMIN_EMAIL"]
    ADMIN_PASSWORD: str = os.environ["ADMIN_PASSWORD"]
    ADMIN_ID: int = int(os.environ["ADMIN_ID"])

    # --------------------------
    # Search
    # --------------------------
    MAX_TEXT_LENGTH: int = int(os.environ["MAX_TEXT_LENGTH"])
    DEFAULT_TOP_K: int = int(os.environ["DEFAULT_TOP_K"])
    DEFAULT_WEIGHT_IMAGE: float = float(os.environ["DEFAULT_WEIGHT_IMAGE"])
    DEFAULT_WEIGHT_TEXT: float = float(os.environ["DEFAULT_WEIGHT_TEXT"])

    # --------------------------
    # Server & CORS
    # --------------------------
    API_PORT: int = int(os.environ["API_PORT"])
    CORS_ORIGINS: list[str] = os.environ["CORS_ORIGINS"].split(",")
    BASE_URL: str = os.environ["BASE_URL"]

    # --------------------------
    # Groq API
    # --------------------------
    GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
    GROQ_API_URL: str = os.environ["GROQ_API_URL"]

    # --------------------------
    # Hybrid Storage Config
    # --------------------------
    USE_CLOUD: bool = os.environ.get("USE_CLOUD", "False").lower() == "true"
    
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "")


settings = Settings()
