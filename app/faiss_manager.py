# app/faiss_manager.py
import os
import faiss
import numpy as np

INDEX_DIR = "/faiss_index"
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
DIM = 512

class FaissManager:
    def __init__(self):
        os.makedirs(INDEX_DIR, exist_ok=True)
        self.index = None
        self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(INDEX_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
                # if index read but not wrapped in IDMap, ensure type
                if not isinstance(self.index, faiss.IndexIDMap2):
                    self.index = faiss.IndexIDMap2(self.index)
            except Exception:
                # fallback to new index
                self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(DIM))
        else:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(DIM))

    def add_vector(self, vector: np.ndarray, id_: int):
        vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        ids = np.array([id_], dtype="int64")
        # remove any existing id first
        try:
            self.index.remove_ids(np.array([id_], dtype="int64"))
        except Exception:
            pass
        self.index.add_with_ids(vec, ids)
        self.save()

    def save(self):
        faiss.write_index(self.index, INDEX_PATH)

    def search(self, vector: np.ndarray, top_k: int = 10):
        vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        scores, ids = self.index.search(vec, top_k)
        return ids[0].tolist(), scores[0].tolist()
