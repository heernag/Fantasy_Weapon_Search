"""환경변수와 프로젝트 상대경로를 한곳에서 관리하는 설정 모듈."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# `.env`도 현재 작업 디렉터리가 아니라 이 저장소의 루트에서 찾는다.
# 예: 저장소 밖의 다른 작업 폴더에서 스크립트를 실행해도 같은 설정을 읽는다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """`FWS_` 환경변수를 읽고 실행 위치와 무관한 절대경로를 제공한다."""

    model_config = SettingsConfigDict(
        env_prefix="FWS_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
    )

    # 소스 파일 위치로 루트를 계산하므로 저장소가 어느 드라이브/폴더로 이동해도
    # 상대경로 설정은 동일하게 동작한다. 사용자가 이 값을 설정할 필요는 없다.
    project_root: Path = PROJECT_ROOT

    model_name: str = "ViT-B-16"
    pretrained: str = "laion2b_s34b_b88k"
    device: str = "cpu"
    batch_size: int = 32

    # 아래 경로들은 기본적으로 project_root 기준이다. 다른 저장소나 볼륨을
    # 사용할 때만 FWS_* 환경변수에 절대경로를 지정하면 된다.
    metadata_path: Path = Path("data/metadata/final_search_assets.jsonl")
    image_root: Path = Path(".")
    index_path: Path = Path("storage/indexes/weapons.faiss")
    index_ids_path: Path = Path("storage/indexes/weapon_ids.json")
    log_path: Path = Path("storage/logs/search.jsonl")
    model_cache: Path = Path(".cache/openclip")
    adapter_checkpoint: Path = Path("models/clip_adapter_vit_b16/best_adapter.pt")
    adapter_config: Path = Path("models/clip_adapter_vit_b16/config.json")
    adapter_embeddings: Path = Path(
        "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/image_embeddings.npy"
    )
    adapter_ids: Path = Path("embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/asset_ids.json")
    adapter_model_info: Path = Path(
        "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/model_info.json"
    )
    final_manifest_path: Path = Path("data/metadata/final_manifest.json")
    service_manifest_path: Path = Path("storage/indexes/service_manifest.json")
    # [미사용] 읽는 곳이 없다. 번역 모델 캐시 경로는
    # src/retrieval/search_service.py가 `self.root / ".cache/translation"`으로
    # 하드코딩하므로 이 설정을 바꿔도 아무 효과가 없다. AI 담당 모듈을 고치지
    # 않기로 했으므로 설정만 주석 처리한다.
    # translation_cache: Path = Path(".cache/translation")
    cors_origins: str = ""

    # 기본은 꺼져 있다. 켜면 서버 시작 시(요청을 받기 전) 한국어 번역 모델을
    # 한 번 실제로 태워 첫 한국어 검색이 느려지는 것을 막는다. 로컬 개발·테스트에서
    # TestClient를 반복 생성할 때마다 이 비용(수 초)을 물지 않도록 기본값을
    # 꺼둔다. 운영 배포에서는 켜서 실행한다(Dockerfile 기본값 참고).
    preload_translation_model: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def absolute(self, path: Path) -> Path:
        """절대경로는 보존하고 상대경로만 프로젝트 루트 아래로 해석한다."""
        return path if path.is_absolute() else self.project_root / path


@lru_cache
def get_settings() -> Settings:
    """한 프로세스에서 동일 설정을 재사용해 환경변수 재해석을 방지한다."""
    return Settings()
