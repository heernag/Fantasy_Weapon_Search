from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from src.retrieval.search_service import (
    WeaponSearchService as BaseWeaponSearchService,
)


class ResidualAdapter(nn.Module):
    def __init__(self, dimension: int = 512, hidden_dimension: int = 128):
        super().__init__()
        self.down = nn.Linear(dimension, hidden_dimension)
        self.activation = nn.GELU()
        self.up = nn.Linear(hidden_dimension, dimension)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return F.normalize(
            features + self.up(self.activation(self.down(features))),
            dim=-1,
        )


class MultimodalAdapter(nn.Module):
    def __init__(self, dimension: int = 512, hidden_dimension: int = 128):
        super().__init__()
        self.image_adapter = ResidualAdapter(dimension, hidden_dimension)
        self.text_adapter = ResidualAdapter(dimension, hidden_dimension)


class WeaponSearchService(BaseWeaponSearchService):
    """Final search service using the custom-trained multimodal adapters.

    Its public search methods and response format are identical to the baseline
    WeaponSearchService, so the API layer only needs to change the import path.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        device: str | None = None,
        enable_korean_translation: bool = True,
    ) -> None:
        super().__init__(
            root=root,
            device=device,
            enable_korean_translation=enable_korean_translation,
        )

        self.embedding_dir = (
            self.root
            / "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter"
        )
        self.image_embeddings, adapted_ids = self._load_embeddings()
        if adapted_ids != self.asset_ids:
            raise ValueError(
                "Adapted embedding asset IDs do not match baseline asset IDs."
            )

        self.adapter_checkpoint = (
            self.root / "models/clip_adapter_vit_b16/best_adapter.pt"
        )
        checkpoint = torch.load(
            self.adapter_checkpoint,
            map_location=self.device,
            weights_only=True,
        )
        self.adapter = MultimodalAdapter(
            dimension=checkpoint["embedding_dimension"],
            hidden_dimension=checkpoint["hidden_dimension"],
        ).to(self.device)
        self.adapter.load_state_dict(checkpoint["model_state_dict"])
        self.adapter.eval()
        self.model_variant = "ViT-B-16 + custom residual adapters"

    def _adapt_vector(
        self,
        vector: np.ndarray,
        modality: str,
    ) -> np.ndarray:
        tensor = torch.from_numpy(vector).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            if modality == "image":
                adapted = self.adapter.image_adapter(tensor)
            elif modality == "text":
                adapted = self.adapter.text_adapter(tensor)
            else:
                raise ValueError(f"Unsupported modality: {modality}")
        return adapted.cpu().numpy().astype(np.float32)[0]

    def _encode_text(self, text: str) -> tuple[np.ndarray, str | None]:
        base_vector, translated = super()._encode_text(text)
        return self._adapt_vector(base_vector, "text"), translated

    def _encode_image(
        self,
        image: str | Path | bytes | Image.Image,
    ) -> tuple[np.ndarray, Path | None]:
        base_vector, image_path = super()._encode_image(image)
        return self._adapt_vector(base_vector, "image"), image_path
