"""최종 모델·임베딩·FAISS·메타데이터가 같은 서비스 번들인지 검증한다."""

import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def asset_ids_digest(asset_ids: list[str]) -> str:
    payload = json.dumps(asset_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _index_and_ids(store):
    index = getattr(store, "faiss_index", None) or store.index
    asset_ids = getattr(store, "faiss_asset_ids", None) or store.asset_ids
    return index, asset_ids


def build_service_manifest(settings, repository, store) -> dict:
    index, asset_ids = _index_and_ids(store)
    config_path = settings.absolute(settings.adapter_config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = {
        "adapter": settings.absolute(settings.adapter_checkpoint),
        "embedding": settings.absolute(settings.adapter_embeddings),
        "asset_ids": settings.absolute(settings.adapter_ids),
        "metadata": settings.absolute(settings.metadata_path),
        "index": settings.absolute(settings.index_path),
    }
    return {
        "schema_version": 1,
        "service_version": "final-adapter-v1",
        "model": {
            "name": settings.model_name,
            "pretrained": settings.pretrained,
            "adapter_epoch": config["best_epoch"],
            "embedding_dimension": index.d,
            "dtype": "float32",
            "normalized": True,
        },
        "asset_count": len(asset_ids),
        "asset_ids_sha256": asset_ids_digest(asset_ids),
        "files": {
            name: {"path": str(path.relative_to(settings.project_root)).replace("\\", "/"), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
    }


def _require_equal(field: str, actual, expected) -> None:
    if actual != expected:
        raise ValueError(f"서비스 manifest 불일치: {field}: {actual!r} != {expected!r}")


def validate_service_manifest(manifest: dict, settings, repository, store) -> dict:
    index, asset_ids = _index_and_ids(store)
    _require_equal("model.name", manifest["model"]["name"], settings.model_name)
    _require_equal("model.pretrained", manifest["model"]["pretrained"], settings.pretrained)
    _require_equal("model.embedding_dimension", manifest["model"]["embedding_dimension"], index.d)
    _require_equal("asset_count", manifest["asset_count"], len(asset_ids))
    _require_equal("index.ntotal", index.ntotal, len(asset_ids))
    _require_equal("asset_ids", set(asset_ids), set(repository.by_id))
    _require_equal("asset_ids_sha256", manifest["asset_ids_sha256"], asset_ids_digest(asset_ids))

    path_fields = {
        "adapter": settings.adapter_checkpoint,
        "embedding": settings.adapter_embeddings,
        "asset_ids": settings.adapter_ids,
        "metadata": settings.metadata_path,
        "index": settings.index_path,
    }
    for name, configured_path in path_fields.items():
        expected_hash = sha256_file(settings.absolute(configured_path))
        _require_equal(f"{name}.sha256", manifest["files"][name]["sha256"], expected_hash)
    return manifest


def load_and_validate_service_manifest(settings, repository, store) -> dict:
    path = settings.absolute(settings.service_manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return validate_service_manifest(manifest, settings, repository, store)
