"""검증된 어댑터 임베딩으로 최종 FAISS 인덱스와 서비스 manifest를 만든다."""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.repository import AssetRepository
from app.service_manifest import build_service_manifest, validate_service_manifest
from app.vector_store import FaissVectorStore


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_final_data_manifest(settings, repository: AssetRepository) -> None:
    manifest = json.loads(settings.absolute(settings.final_manifest_path).read_text(encoding="utf-8"))
    if manifest.get("status") != "final":
        raise ValueError("final_manifest.status가 final이 아닙니다")
    source = manifest["source_metadata"]
    source_path = settings.absolute(Path(source["path"]))
    if sha256(source_path) != source["sha256"]:
        raise ValueError("final_manifest source_metadata.sha256 불일치")
    if source["asset_count"] != len(repository.assets):
        raise ValueError("final_manifest asset_count 불일치")


def atomic_write_index(index, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".faiss.tmp", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        faiss.write_index(index, str(temporary))
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".tmp", mode="w", encoding="utf-8", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    settings = get_settings()
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    validate_final_data_manifest(settings, repository)

    embeddings = np.load(settings.absolute(settings.adapter_embeddings)).astype("float32")
    asset_ids = json.loads(settings.absolute(settings.adapter_ids).read_text(encoding="utf-8"))
    model_info = json.loads(settings.absolute(settings.adapter_model_info).read_text(encoding="utf-8"))
    if embeddings.shape != (len(asset_ids), model_info["embedding_dimension"]):
        raise ValueError("어댑터 임베딩 shape와 model_info가 일치하지 않습니다")
    if asset_ids != [asset["asset_id"] for asset in repository.assets]:
        raise ValueError("어댑터 asset_id 순서와 최종 메타데이터가 일치하지 않습니다")
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError("어댑터 임베딩이 L2 정규화되어 있지 않습니다")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    index_path = settings.absolute(settings.index_path)
    ids_path = settings.absolute(settings.index_ids_path)
    atomic_write_index(index, index_path)
    atomic_write_text(ids_path, json.dumps(asset_ids, ensure_ascii=False, indent=2))

    store = FaissVectorStore(index_path, ids_path)
    manifest = build_service_manifest(settings, repository, store)
    validate_service_manifest(manifest, settings, repository, store)
    atomic_write_text(
        settings.absolute(settings.service_manifest_path),
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    print(f"saved final adapter index: {index.ntotal} vectors x {index.d}")


if __name__ == "__main__":
    main()
