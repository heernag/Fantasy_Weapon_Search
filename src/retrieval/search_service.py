from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import open_clip
import torch
from PIL import Image
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "data/metadata/final_search_assets.jsonl"
EMBEDDING_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k"

MODEL_NAME = "ViT-B-16"
PRETRAINED = "laion2b_s34b_b88k"
TRANSLATION_MODEL = "Helsinki-NLP/opus-mt-ko-en"
IMAGE_WEIGHT = 0.4
TEXT_WEIGHT = 0.6

SCALAR_FILTERS = {
    "visual_style",
    "category",
    "subcategory",
    "primary_color",
    "grade",
}
LIST_FILTERS = {
    "colors",
    "materials",
    "elements",
    "shape_tags",
}


class WeaponSearchService:
    """Reusable OpenCLIP search service for the API layer.

    Create one instance when the API starts and reuse it for every request.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        device: str | None = None,
        enable_korean_translation: bool = True,
    ) -> None:
        self.root = Path(root).resolve() if root else ROOT
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.enable_korean_translation = enable_korean_translation

        self.metadata_path = (
            self.root / "data/metadata/final_search_assets.jsonl"
        )
        self.embedding_dir = (
            self.root / "embeddings/ViT-B-16_laion2b_s34b_b88k"
        )

        self.records = self._load_metadata()
        self.metadata = {
            record["asset_id"]: record for record in self.records
        }
        self.image_embeddings, self.asset_ids = self._load_embeddings()

        missing = [
            asset_id
            for asset_id in self.asset_ids
            if asset_id not in self.metadata
        ]
        if missing:
            raise ValueError(f"Metadata missing asset IDs: {missing[:5]}")

        self.model, _, self.preprocess = (
            open_clip.create_model_and_transforms(
                MODEL_NAME,
                pretrained=PRETRAINED,
                device=self.device,
            )
        )
        self.tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        self.model.eval()

        self.translation_tokenizer = None
        self.translation_model = None

    def _load_metadata(self) -> list[dict[str, Any]]:
        rows = []
        with self.metadata_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def _load_embeddings(self) -> tuple[np.ndarray, list[str]]:
        embeddings = np.load(
            self.embedding_dir / "image_embeddings.npy"
        ).astype(np.float32)

        with (self.embedding_dir / "asset_ids.json").open(
            "r", encoding="utf-8"
        ) as file:
            asset_ids = json.load(file)

        if embeddings.shape[0] != len(asset_ids):
            raise ValueError(
                "Embedding row count and asset ID count do not match."
            )
        return embeddings, asset_ids

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("Cannot normalize a zero vector.")
        return vector / norm

    @staticmethod
    def _contains_korean(text: str) -> bool:
        return any("\uac00" <= character <= "\ud7a3" for character in text)

    def _load_translation_model(self) -> None:
        if self.translation_model is not None:
            return

        self.translation_tokenizer = AutoTokenizer.from_pretrained(
            TRANSLATION_MODEL
        )
        self.translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            TRANSLATION_MODEL
        ).to(self.device)
        self.translation_model.eval()

    def _prepare_text(self, text: str) -> tuple[str, str | None]:
        text = text.strip()
        if not text:
            raise ValueError("Search text must not be empty.")

        if not (
            self.enable_korean_translation
            and self._contains_korean(text)
        ):
            return text, None

        self._load_translation_model()
        inputs = self.translation_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
        ).to(self.device)

        with torch.inference_mode():
            generated = self.translation_model.generate(
                **inputs,
                max_new_tokens=64,
            )

        translated = self.translation_tokenizer.decode(
            generated[0],
            skip_special_tokens=True,
        )
        return translated, translated

    def _encode_text(self, text: str) -> tuple[np.ndarray, str | None]:
        model_text, translated = self._prepare_text(text)
        tokens = self.tokenizer([model_text]).to(self.device)

        with torch.inference_mode():
            embedding = self.model.encode_text(tokens)
            embedding /= embedding.norm(dim=-1, keepdim=True)

        vector = embedding.cpu().numpy().astype(np.float32)[0]
        return vector, translated

    def _load_query_image(
        self,
        image: str | Path | bytes | Image.Image,
    ) -> tuple[Image.Image, Path | None]:
        if isinstance(image, Image.Image):
            return image.convert("RGB"), None

        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image)).convert("RGB"), None

        image_path = Path(image)
        if not image_path.is_absolute():
            image_path = self.root / image_path
        image_path = image_path.resolve()

        if not image_path.exists():
            raise FileNotFoundError(image_path)

        with Image.open(image_path) as opened:
            loaded = opened.convert("RGB")
        return loaded, image_path

    def _encode_image(
        self,
        image: str | Path | bytes | Image.Image,
    ) -> tuple[np.ndarray, Path | None]:
        loaded, image_path = self._load_query_image(image)
        tensor = self.preprocess(loaded).unsqueeze(0).to(self.device)

        with torch.inference_mode():
            embedding = self.model.encode_image(tensor)
            embedding /= embedding.norm(dim=-1, keepdim=True)

        vector = embedding.cpu().numpy().astype(np.float32)[0]
        return vector, image_path

    @staticmethod
    def _matches_filters(
        record: dict[str, Any],
        filters: dict[str, Any] | None,
    ) -> bool:
        if not filters:
            return True

        unsupported = set(filters) - SCALAR_FILTERS - LIST_FILTERS
        if unsupported:
            raise ValueError(
                f"Unsupported filters: {sorted(unsupported)}"
            )

        for field, expected in filters.items():
            if expected is None:
                continue

            actual = record.get(field)
            if field in SCALAR_FILTERS:
                if actual != expected:
                    return False
                continue

            expected_values = (
                [expected]
                if isinstance(expected, str)
                else list(expected)
            )
            actual_values = set(actual or [])
            if not all(value in actual_values for value in expected_values):
                return False

        return True

    def _candidate_indices(
        self,
        filters: dict[str, Any] | None,
        excluded_asset_ids: set[str] | None = None,
        excluded_path: Path | None = None,
    ) -> list[int]:
        excluded_asset_ids = excluded_asset_ids or set()
        indices = []

        for index, asset_id in enumerate(self.asset_ids):
            if asset_id in excluded_asset_ids:
                continue

            record = self.metadata[asset_id]
            if not self._matches_filters(record, filters):
                continue

            if excluded_path is not None:
                candidate_path = (
                    self.root / record["processed_file"]
                ).resolve()
                if candidate_path == excluded_path:
                    continue

            indices.append(index)

        if not indices:
            raise ValueError("No assets match the search conditions.")
        return indices

    @staticmethod
    def _validate_top_k(top_k: int) -> None:
        if not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100.")

    def _result_record(
        self,
        index: int,
        score: float,
        image_score: float | None = None,
        text_score: float | None = None,
    ) -> dict[str, Any]:
        asset_id = self.asset_ids[index]
        record = self.metadata[asset_id]
        result = {
            "asset_id": asset_id,
            "score": round(float(score), 6),
            "visual_style": record.get("visual_style"),
            "category": record.get("category"),
            "subcategory": record.get("subcategory"),
            "primary_color": record.get("primary_color"),
            "colors": record.get("colors", []),
            "materials": record.get("materials", []),
            "elements": record.get("elements", []),
            "caption_en": record.get("caption_en"),
            "caption_ko": record.get("caption_ko"),
            "image_path": record.get("processed_file"),
            "source_url": record.get("source_url"),
            "license": record.get("license"),
        }
        if image_score is not None:
            result["image_score"] = round(float(image_score), 6)
        if text_score is not None:
            result["text_score"] = round(float(text_score), 6)
        if image_score is not None and text_score is not None:
            result["combined_score"] = result["score"]
        return result

    def _rank(
        self,
        scores: np.ndarray,
        candidate_indices: list[int],
        top_k: int,
        image_scores: np.ndarray | None = None,
        text_scores: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        ranked = sorted(
            candidate_indices,
            key=lambda index: float(scores[index]),
            reverse=True,
        )[:top_k]

        return [
            self._result_record(
                index,
                scores[index],
                None if image_scores is None else image_scores[index],
                None if text_scores is None else text_scores[index],
            )
            for index in ranked
        ]

    def search_text(
        self,
        text: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        vector, translated = self._encode_text(text)
        scores = self.image_embeddings @ vector
        candidates = self._candidate_indices(filters)

        return {
            "search_type": "text",
            "query_text": text,
            "translated_text": translated,
            "candidate_count": len(candidates),
            "results": self._rank(scores, candidates, top_k),
        }

    def search_image(
        self,
        image: str | Path | bytes | Image.Image,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        include_self: bool = False,
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        vector, image_path = self._encode_image(image)
        scores = self.image_embeddings @ vector
        excluded_path = None if include_self else image_path
        candidates = self._candidate_indices(
            filters,
            excluded_path=excluded_path,
        )

        return {
            "search_type": "image",
            "candidate_count": len(candidates),
            "results": self._rank(scores, candidates, top_k),
        }

    def search_multimodal(
        self,
        image: str | Path | bytes | Image.Image,
        text: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        image_weight: float = IMAGE_WEIGHT,
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        if not 0 <= image_weight <= 1:
            raise ValueError("image_weight must be between 0 and 1.")

        text_weight = 1.0 - image_weight
        image_vector, image_path = self._encode_image(image)
        text_vector, translated = self._encode_text(text)
        combined_vector = self._normalize(
            image_weight * image_vector + text_weight * text_vector
        )

        combined_scores = self.image_embeddings @ combined_vector
        image_scores = self.image_embeddings @ image_vector
        text_scores = self.image_embeddings @ text_vector
        candidates = self._candidate_indices(
            filters,
            excluded_path=image_path,
        )

        return {
            "search_type": "multimodal",
            "query_text": text,
            "translated_text": translated,
            "image_weight": image_weight,
            "text_weight": text_weight,
            "candidate_count": len(candidates),
            "results": self._rank(
                combined_scores,
                candidates,
                top_k,
                image_scores=image_scores,
                text_scores=text_scores,
            ),
        }
