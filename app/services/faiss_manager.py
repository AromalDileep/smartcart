# app/faiss_manager.py
import os
import shutil
from datetime import datetime

import faiss
import numpy as np

from app.core.config import settings




class FaissManager:
    def __init__(self):
        self.index_dir = settings.FAISS_INDEX_DIR
        self.index_path = os.path.join(self.index_dir, "index.faiss")
        self.dim = settings.FAISS_DIM
        
        os.makedirs(self.index_dir, exist_ok=True)
        self.index = None
        self._load_or_create()

    # -----------------------------------------------
    def _load_or_create(self):
        """Load existing FAISS index or create a new one."""
        if os.path.exists(self.index_path):
            try:
                idx = faiss.read_index(self.index_path)
                self.index = faiss.IndexIDMap2(idx)
            except Exception:
                self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))
        else:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

    # -----------------------------------------------
    def save(self):
        """Save FAISS index to disk."""
        faiss.write_index(self.index, self.index_path)

    # -----------------------------------------------
    def add_vector(self, vector: np.ndarray, id_: int):
        """Add/update one vector"""
        vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        ids = np.array([id_], dtype="int64")

        try:
            self.index.remove_ids(ids)
        except Exception:
            pass

        self.index.add_with_ids(vec, ids)
        self.save()

    # -----------------------------------------------
    def remove_vector(self, product_id: int):
        """Remove vector by FAISS ID"""
        try:
            self.index.remove_ids(np.array([product_id], dtype="int64"))
            self.save()
            return True
        except Exception:
            return False

    # -----------------------------------------------
    def search(self, vector: np.ndarray, top_k: int = 10):
        vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        scores, ids = self.index.search(vec, top_k)
        return ids[0].tolist(), scores[0].tolist()

    # -----------------------------------------------
    def rebuild(self, vectors, ids):
        """Fully rebuild FAISS from scratch"""
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

        if vectors and ids:
            vectors_np = np.asarray(vectors, dtype="float32").reshape(len(vectors), -1)
            ids_np = np.asarray(ids, dtype="int64")
            self.index.add_with_ids(vectors_np, ids_np)

        self.save()

    # -----------------------------------------------
    def backup_index(self):
        """Backup index file"""
        if not os.path.exists(self.index_path):
            return None

        backup_name = f"index_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.faiss"
        backup_path = os.path.join(self.index_dir, backup_name)

        shutil.copy2(self.index_path, backup_path)
        return backup_path
