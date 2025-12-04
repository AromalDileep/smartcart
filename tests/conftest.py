import pytest
import os
from app.core.config import settings

@pytest.fixture(scope="session", autouse=True)
def patch_db_host():
    """
    Force POSTGRES_HOST to 'localhost' for local testing.
    This runs automatically before any tests.
    """
    # We modify the settings object directly since it's already loaded
    original_host = settings.POSTGRES_HOST
    settings.POSTGRES_HOST = "localhost"
    
    yield
    
    # Restore after tests (though not strictly necessary for session scope)
    settings.POSTGRES_HOST = original_host

@pytest.fixture(scope="session", autouse=True)
def patch_model_path():
    """
    Force MODEL_PATH to a valid HF Hub ID for local testing.
    """
    original_path = settings.MODEL_PATH
    # Use the HF Hub ID so it downloads/caches locally
    settings.MODEL_PATH = "openai/clip-vit-base-patch32"
    
    yield
    
    settings.MODEL_PATH = original_path
