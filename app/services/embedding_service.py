# app/services/embedding_service.py


import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.core.config import settings

MODEL_PATH = settings.MODEL_PATH  # mounted path inside container

class CLIPEmbedder:
    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # load model & processor from local folder
        self.model = CLIPModel.from_pretrained(MODEL_PATH).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_PATH)

    def embed_image(self, image_path: str) -> np.ndarray:
        """
        Returns a normalized (L2) 512-d float32 numpy vector.
        """
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        # move tensors to device
        for k, v in inputs.items():
            inputs[k] = v.to(self.device)
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)  # (1, 512)
        vec = outputs.cpu().numpy().astype("float32").reshape(-1)  # shape (512,)
        # normalize to unit length for cosine similarity with IndexFlatIP
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
