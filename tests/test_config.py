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


def test_translation_preload_defaults_off():
    # 로컬 개발·테스트에서 서버(TestClient 포함)를 반복 기동할 때마다 번역 모델
    # 로딩 비용을 물지 않도록 기본값은 꺼져 있어야 한다. 운영은 Dockerfile의
    # FWS_PRELOAD_TRANSLATION_MODEL=true로 켠다.
    settings = Settings(_env_file=None)

    assert settings.preload_translation_model is False


def test_translation_preload_can_be_enabled_via_env(monkeypatch):
    monkeypatch.setenv("FWS_PRELOAD_TRANSLATION_MODEL", "true")

    settings = Settings(_env_file=None)

    assert settings.preload_translation_model is True
