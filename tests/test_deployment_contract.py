import json
import re
from pathlib import Path, PurePosixPath

from app.main import app
from app.main import configure_cors
from app.schemas import MultimodalWeights
from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def test_multimodal_defaults_match_validated_search_weights():
    weights = MultimodalWeights()
    assert weights.image_weight == 0.4
    assert weights.text_weight == 0.6

    openapi = app.openapi()
    request_schema = openapi["paths"]["/search/multimodal"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]
    schema_name = request_schema["$ref"].rsplit("/", 1)[-1]
    properties = openapi["components"]["schemas"][schema_name]["properties"]
    assert properties["image_weight"]["default"] == 0.4
    assert properties["text_weight"]["default"] == 0.6


def test_docker_image_copies_every_local_package_the_api_imports():
    # 에셋만 검사하면 `src` 같은 코드 디렉터리 누락을 놓쳐 컨테이너가 import 단계에서 죽는다.
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copied = {
        PurePosixPath(source).parts[0]
        for source in re.findall(r"^COPY\s+(\S+)\s+\S+\s*$", dockerfile, flags=re.MULTILINE)
    }

    imported = set()
    for path in sorted((ROOT / "app").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for name in re.findall(r"^(?:from|import)\s+([A-Za-z_]\w*)", source, flags=re.MULTILINE):
            if (ROOT / name).is_dir():
                imported.add(name)

    assert "src" in imported
    assert not sorted(imported - copied)


def test_docker_image_includes_every_searchable_asset_file():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copied_directories = []
    for source in re.findall(r"^COPY\s+(\S+)\s+\S+\s*$", dockerfile, flags=re.MULTILINE):
        path = PurePosixPath(source)
        if path.suffix == "":
            copied_directories.append(path)

    metadata_path = ROOT / "data/metadata/final_search_assets.jsonl"
    assets = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines() if line]
    missing = [
        asset["processed_file"]
        for asset in assets
        if not any(
            PurePosixPath(asset["processed_file"]).is_relative_to(directory)
            for directory in copied_directories
        )
    ]

    assert not missing, f"Docker 이미지에 포함되지 않는 검색 에셋이 있습니다: {missing[:5]}"


def test_cors_is_enabled_only_for_explicit_origins():
    no_cors = FastAPI()
    configure_cors(no_cors, [])
    with TestClient(no_cors) as client:
        response = client.options(
            "/anything",
            headers={"Origin": "https://frontend.example", "Access-Control-Request-Method": "GET"},
        )
    assert "access-control-allow-origin" not in response.headers

    allowed = FastAPI()
    configure_cors(allowed, ["https://frontend.example"])
    with TestClient(allowed) as client:
        response = client.options(
            "/anything",
            headers={"Origin": "https://frontend.example", "Access-Control-Request-Method": "GET"},
        )
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"


def test_docker_includes_final_adapter_bundle():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copied = set(re.findall(r"^COPY\s+(\S+)\s+\S+\s*$", dockerfile, flags=re.MULTILINE))

    assert "models/clip_adapter_vit_b16" in copied
    assert "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter" in copied
    assert "storage/indexes" in copied
