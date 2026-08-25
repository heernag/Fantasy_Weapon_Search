from __future__ import annotations

import json
from pathlib import Path

import faiss
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

        index = faiss.read_index(
            str(self.root / "storage/indexes/weapons.faiss")
        )
        with (self.root / "storage/indexes/weapon_ids.json").open(
            "r", encoding="utf-8"
        ) as file:
            index_asset_ids = json.load(file)
        self._configure_faiss_index(index, index_asset_ids)

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

    def _configure_faiss_index(
        self,
        index,
        index_asset_ids: list[str],
    ) -> None:
        embedding_dimension = self.image_embeddings.shape[1]
        if index.d != embedding_dimension:
            raise ValueError(
                "FAISS dimension does not match adapter embedding dimension."
            )
        if index.ntotal != len(self.asset_ids):
            raise ValueError(
                "FAISS vector count does not match adapter asset count."
            )
        if index_asset_ids != self.asset_ids:
            raise ValueError(
                "FAISS asset ID order does not match adapter asset ID order."
            )
        self.faiss_index = index
        self.faiss_asset_ids = list(index_asset_ids)

    def _rank_with_faiss(
        self,
        query_vector: np.ndarray,
        candidate_indices: list[int],
        top_k: int,
    ) -> list[tuple[int, float]]:
        candidates = set(candidate_indices)
        if not candidates:
            return []

        query = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        if query.shape[1] != self.faiss_index.d:
            raise ValueError("Query dimension does not match FAISS dimension.")

        fetch_k = min(max(top_k, 1), self.faiss_index.ntotal)
        while True:
            scores, positions = self.faiss_index.search(query, fetch_k)
            matches = [
                (int(position), float(score))
                for position, score in zip(positions[0], scores[0])
                if position >= 0 and int(position) in candidates
            ]
            if len(matches) >= top_k or fetch_k >= self.faiss_index.ntotal:
                return matches[:top_k]
            fetch_k = min(fetch_k * 2, self.faiss_index.ntotal)

    def _faiss_results(
        self,
        query_vector: np.ndarray,
        candidate_indices: list[int],
        top_k: int,
        image_vector: np.ndarray | None = None,
        text_vector: np.ndarray | None = None,
    ) -> list[dict]:
        ranked = self._rank_with_faiss(
            query_vector,
            candidate_indices,
            top_k,
        )
        results = []
        for index, score in ranked:
            image_score = None
            text_score = None
            if image_vector is not None and text_vector is not None:
                candidate = np.asarray(
                    self.faiss_index.reconstruct(index), dtype="float32"
                )
                image_score = float(np.dot(candidate, image_vector))
                text_score = float(np.dot(candidate, text_vector))
            results.append(
                self._result_record(index, score, image_score, text_score)
            )
        return results

    @staticmethod
    def _combine_vectors(
        image_vector: np.ndarray,
        text_vector: np.ndarray,
        image_weight: float,
    ) -> np.ndarray:
        image = np.asarray(image_vector, dtype="float32")
        text = np.asarray(text_vector, dtype="float32")
        if image.shape != text.shape:
            raise ValueError(
                f"Image and text vector shape must match: {image.shape} != {text.shape}"
            )
        combined = image_weight * image + (1.0 - image_weight) * text
        norm = np.linalg.norm(combined)
        if norm <= 1e-12:
            raise ValueError("Cannot normalize a zero vector.")
        return (combined / norm).astype("float32")

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
        vector = adapted.cpu().numpy().astype(np.float32)[0]
        return self._normalize(vector).astype(np.float32)

    def _encode_text(self, text: str) -> tuple[np.ndarray, str | None]:
        base_vector, translated = super()._encode_text(text)
        return self._adapt_vector(base_vector, "text"), translated

    def _encode_image(
        self,
        image: str | Path | bytes | Image.Image,
    ) -> tuple[np.ndarray, Path | None]:
        base_vector, image_path = super()._encode_image(image)
        return self._adapt_vector(base_vector, "image"), image_path

    def search_text(
        self,
        text: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> dict:
        self._validate_top_k(top_k)
        vector, translated = self._encode_text(text)
        candidates = self._candidate_indices(filters)
        return {
            "search_type": "text",
            "query_text": text,
            "translated_text": translated,
            "candidate_count": len(candidates),
            "results": self._faiss_results(vector, candidates, top_k),
        }

    def search_image(
        self,
        image,
        top_k: int = 10,
        filters: dict | None = None,
        include_self: bool = False,
        excluded_asset_ids: set[str] | None = None,
    ) -> dict:
        self._validate_top_k(top_k)
        vector, image_path = self._encode_image(image)
        excluded_path = None if include_self else image_path
        excluded_ids = set() if include_self else (excluded_asset_ids or set())
        candidates = self._candidate_indices(
            filters,
            excluded_asset_ids=excluded_ids,
            excluded_path=excluded_path,
        )
        return {
            "search_type": "image",
            "candidate_count": len(candidates),
            "results": self._faiss_results(vector, candidates, top_k),
        }

    def search_multimodal(
        self,
        image,
        text: str,
        top_k: int = 10,
        filters: dict | None = None,
        image_weight: float = 0.4,
        excluded_asset_ids: set[str] | None = None,
    ) -> dict:
        self._validate_top_k(top_k)
        if not 0 <= image_weight <= 1:
            raise ValueError("image_weight must be between 0 and 1.")

        text_weight = 1.0 - image_weight
        image_vector, image_path = self._encode_image(image)
        text_vector, translated = self._encode_text(text)
        combined_vector = self._combine_vectors(
            image_vector, text_vector, image_weight
        )
        candidates = self._candidate_indices(
            filters,
            excluded_asset_ids=excluded_asset_ids,
            excluded_path=image_path,
        )
        return {
            "search_type": "multimodal",
            "query_text": text,
            "translated_text": translated,
            "image_weight": image_weight,
            "text_weight": text_weight,
            "candidate_count": len(candidates),
            "results": self._faiss_results(
                combined_vector,
                candidates,
                top_k,
                image_vector=image_vector,
                text_vector=text_vector,
            ),
        }
