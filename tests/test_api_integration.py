import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_real_model_search_endpoints():
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["assets"] == 1391
        assert health.json()["vectors"] == 1391
        assert health.json()["model"]["name"] == "ViT-B-16"
        assert health.json()["model"]["pretrained"] == "laion2b_s34b_b88k"
        assert health.json()["model"]["integration_status"] == "final_adapter"
        assert health.json()["service_version"] == "final-adapter-v1"

        inventory = client.get("/filters")
        assert inventory.status_code == 200
        assert inventory.json()["category"][0]["value"] == "sword"

        detail = client.get("/assets/asset_000057")
        assert detail.status_code == 200
        assert detail.json()["metadata"]["category"] == "arrow"

        illustration = client.get("/assets/asset_001572")
        assert illustration.status_code == 200
        assert illustration.json()["image_url"] == "/images/illustration/asset_001572.png"
        assert client.get(illustration.json()["image_url"]).status_code == 200

        rendered_icon = client.get("/assets/asset_001332")
        assert rendered_icon.status_code == 200
        assert rendered_icon.json()["image_url"] == "/images/rendered_icon/asset_001332.png"
        assert client.get(rendered_icon.json()["image_url"]).status_code == 200

        text = client.post("/search/text", json={
            "query": "불타는 화살", "top_k": 3, "filters": {"categories": ["arrow"]}
        })
        assert text.status_code == 200
        assert len(text.json()["results"]) == 3
        # 한국어 질의는 영어로 번역한 뒤 검색한다. 번역 구현은
        # src/retrieval/search_service.py 하나뿐이므로 여기서 동작을 고정한다.
        translated = text.json()["translated_text"]
        assert translated and translated != "불타는 화살"
        assert translated.isascii()
        assert all(hit["metadata"]["category"] == "arrow" for hit in text.json()["results"])
        assert text.json()["results"][0]["image_path"].startswith("data/processed/")
        assert text.json()["results"][0]["image_url"].startswith("/images/")

        with image_path.open("rb") as handle:
            image = client.post("/search/image", files={"image": (image_path.name, handle, "image/png")}, data={"top_k": "3"})
        assert image.status_code == 200
        assert all(row["asset_id"] != "asset_000057" for row in image.json()["results"])
        image_hit = image.json()["results"][0]
        assert image_hit["result_text"] == (image_hit["caption_ko"] or image_hit["caption_en"])
        assert image_hit["color"] == image_hit["colors"]
        assert image_hit["element"] == image_hit["elements"]
        assert image_hit["source"] == image_hit["source_url"]
        assert image_hit["image_path"].startswith("data/processed/")
        assert image_hit["image_url"].startswith("/images/")

        with image_path.open("rb") as handle:
            image_with_self = client.post(
                "/search/image",
                files={"image": (image_path.name, handle, "image/png")},
                data={"top_k": "3", "include_self": "true"},
            )
        assert image_with_self.status_code == 200
        assert image_with_self.json()["results"][0]["asset_id"] == "asset_000057"

        with image_path.open("rb") as handle:
            multimodal = client.post(
                "/search/multimodal",
                files={"image": (image_path.name, handle, "image/png")},
                data={"query": "fire arrow", "image_weight": "0.7", "text_weight": "0.3", "top_k": "3"},
            )
        assert multimodal.status_code == 200
        assert len(multimodal.json()["results"]) == 3
        assert multimodal.json()["elapsed_ms"] >= multimodal.json()["search_elapsed_ms"] >= 0
        first = multimodal.json()["results"][0]
        assert first["combined_score"] == first["score"]
        assert isinstance(first["image_score"], float)
        assert isinstance(first["text_score"], float)
        assert first["category"] == first["metadata"]["category"]
        assert first["image_path"].startswith("data/processed/")
        assert first["image_url"].startswith("/images/")

        no_results = client.post(
            "/search/text",
            json={"query": "sword", "filters": {"category": "not-a-real-category"}},
        )
        assert no_results.status_code == 404

        records = [
            json.loads(line)
            for line in (ROOT / "storage/logs/search.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        multimodal_log = next(row for row in reversed(records) if row["query_type"] == "multimodal")
        assert multimodal_log["status_code"] == 200
        assert multimodal_log["service_version"] == "final-adapter-v1"
        assert multimodal_log["elapsed_ms"] >= multimodal_log["search_elapsed_ms"] >= 0

        # 별칭·표기가 섞인 요청이라도 검색에 실제로 적용된 필터가 남아야 한다.
        with TestClient(app) as client:
            logged = client.get(
                "/search/text",
                params={
                    "query": "fire arrow",
                    "top_k": 2,
                    "color": "Orange",
                    "element": "fire",
                    "handedness": "one-handed",
                },
            )
        assert logged.status_code == 200

        records = [
            json.loads(line)
            for line in (ROOT / "storage/logs/search.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert records[-1]["filters"] == {
            "colors": ["orange"],
            "elements": ["fire"],
            "handedness": "one_handed",
        }


def test_images_endpoint_serves_only_final_bundle_files():
    # data/processed에는 최종 1,391개에 포함되지 않은 작업 파일이 남아 있다.
    # 디렉터리를 통째로 공개하면 최종 번들 계약 밖의 이미지가 노출된다.
    orphan = ROOT / "data/processed/pixel_art/asset_000381.png"
    assert orphan.exists()

    with TestClient(app) as client:
        served = client.get("/images/illustration/asset_001572.png")
        blocked = client.get("/images/pixel_art/asset_000381.png")
        # `../`는 클라이언트가 정규화해 서버까지 오지 않을 수 있으므로
        # 인코딩된 형태로 라우트가 직접 받도록 한다.
        traversals = [
            client.get("/images/%2e%2e/%2e%2e/data/metadata/final_search_assets.jsonl"),
            client.get("/images/pixel_art/%2e%2e/%2e%2e/metadata/final_search_assets.jsonl"),
        ]

    assert served.status_code == 200
    assert blocked.status_code == 404
    assert [response.status_code for response in traversals] == [404, 404]
