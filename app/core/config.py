import os
from dotenv import load_dotenv

load_dotenv()


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
    CORS_ORIGINS: list = os.environ["CORS_ORIGINS"].split(",")
    BASE_URL: str = os.environ["BASE_URL"]

    # --------------------------
    # Groq API
    # --------------------------
    GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
    GROQ_API_URL: str = os.environ["GROQ_API_URL"]


settings = Settings()
