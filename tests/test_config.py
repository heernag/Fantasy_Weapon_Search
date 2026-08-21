"""저장소가 다른 폴더로 이동해도 경로 해석 규칙이 유지되는지 확인한다."""

from pathlib import Path

from app.config import Settings


def test_relative_paths_are_resolved_from_project_root(tmp_path):
    settings = Settings(project_root=tmp_path, model_cache=Path(".cache/openclip"))

    assert settings.absolute(settings.model_cache) == tmp_path / ".cache/openclip"
    assert settings.absolute(Path("storage/indexes/test.faiss")) == (
        tmp_path / "storage/indexes/test.faiss"
    )


def test_absolute_paths_are_not_rebased(tmp_path):
    external_path = (tmp_path / "shared-cache").resolve()
    settings = Settings(project_root=tmp_path)

    assert settings.absolute(external_path) == external_path


def test_final_model_bundle_defaults_are_aligned():
    settings = Settings(_env_file=None)

    assert settings.model_name == "ViT-B-16"
    assert settings.pretrained == "laion2b_s34b_b88k"
    assert settings.adapter_checkpoint == Path("models/clip_adapter_vit_b16/best_adapter.pt")
    assert settings.adapter_embeddings == Path(
        "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/image_embeddings.npy"
    )
    assert settings.service_manifest_path == Path("storage/indexes/service_manifest.json")
