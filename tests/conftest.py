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

@pytest.fixture(scope="session")
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    
    # Use TestClient as a context manager to trigger lifespan events (startup/shutdown)
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session", autouse=True)
def patch_paths(tmp_path_factory):
    """
    Force FAISS_INDEX_DIR and IMAGE_DIR to temp paths.
    """
    original_faiss = settings.FAISS_INDEX_DIR
    original_images = settings.IMAGE_DIR
    
    # Create temp dirs
    temp_faiss = tmp_path_factory.mktemp("faiss_index")
    temp_images = tmp_path_factory.mktemp("images")
    
    settings.FAISS_INDEX_DIR = str(temp_faiss)
    settings.IMAGE_DIR = str(temp_images)
    
    yield
    
    settings.FAISS_INDEX_DIR = original_faiss
    settings.IMAGE_DIR = original_images
