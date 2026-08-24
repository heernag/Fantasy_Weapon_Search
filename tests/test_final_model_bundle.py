import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from app.repository import AssetRepository


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeSettings:
    model_name = "ViT-B-16"
    pretrained = "laion2b_s34b_b88k"

    def __init__(self, root: Path):
        self.project_root = root
        self.adapter_checkpoint = Path("adapter.pt")
        self.adapter_config = Path("adapter.json")
        self.adapter_embeddings = Path("embeddings.npy")
        self.adapter_ids = Path("asset_ids.json")
        self.metadata_path = Path("metadata.jsonl")
        self.index_path = Path("weapons.faiss")

    def absolute(self, path: Path) -> Path:
        return self.project_root / path


def make_bundle(tmp_path: Path):
    from app.service_manifest import build_service_manifest

    settings = FakeSettings(tmp_path)
    (tmp_path / "adapter.pt").write_bytes(b"adapter")
    (tmp_path / "adapter.json").write_text(
        json.dumps({"best_epoch": 8, "hidden_dimension": 128}), encoding="utf-8"
    )
    np.save(tmp_path / "embeddings.npy", np.ones((1, 512), dtype=np.float32))
    (tmp_path / "asset_ids.json").write_text('["asset_1"]', encoding="utf-8")
    (tmp_path / "metadata.jsonl").write_text(
        '{"asset_id":"asset_1","processed_file":"data/processed/pixel_art/x.png"}\n',
        encoding="utf-8",
    )
    (tmp_path / "weapons.faiss").write_bytes(b"faiss")
    repository = AssetRepository(tmp_path / "metadata.jsonl")
    store = SimpleNamespace(
        asset_ids=["asset_1"], index=SimpleNamespace(ntotal=1, d=512)
    )
    manifest = build_service_manifest(settings, repository, store)
    return settings, repository, store, manifest


def test_service_manifest_rejects_wrong_model_name(tmp_path):
    from app.service_manifest import validate_service_manifest

    settings, repository, store, manifest = make_bundle(tmp_path)
    manifest["model"]["name"] = "ViT-B-32"

    with pytest.raises(ValueError, match="model.name"):
        validate_service_manifest(manifest, settings, repository, store)


def test_service_manifest_rejects_changed_metadata(tmp_path):
    from app.service_manifest import validate_service_manifest

    settings, repository, store, manifest = make_bundle(tmp_path)
    (tmp_path / "metadata.jsonl").write_text(
        (tmp_path / "metadata.jsonl").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="metadata.sha256"):
        validate_service_manifest(manifest, settings, repository, store)


class IdentityAdapters(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.image_adapter = torch.nn.Identity()
        self.text_adapter = torch.nn.Identity()


def test_official_adapter_normalizes_adapted_vectors():
    from src.retrieval.search_service_adapter import WeaponSearchService

    service = WeaponSearchService.__new__(WeaponSearchService)
    service.device = torch.device("cpu")
    service.adapter = IdentityAdapters()

    text = service._adapt_vector(np.array([3.0, 4.0], dtype=np.float32), "text")
    image = service._adapt_vector(np.array([4.0, 3.0], dtype=np.float32), "image")

    assert text.shape == (2,)
    assert image.shape == (2,)
    assert text.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(text), 1.0)
    np.testing.assert_allclose(np.linalg.norm(image), 1.0)
