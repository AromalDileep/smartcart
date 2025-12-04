# app/services/global_faiss.py

from app.services.faiss_manager import FaissManager
from app.services.embedding_service import CLIPEmbedder

# Global singletons
embedder = None
faiss_mgr = None

def ensure_services():
    """
    Ensures global CLIPEmbedder + FaissManager instances
    are initialized once and shared across the entire app.
    """
    global embedder, faiss_mgr

    if embedder is None:
        embedder = CLIPEmbedder()

    if faiss_mgr is None:
        faiss_mgr = FaissManager()

    return embedder, faiss_mgr
