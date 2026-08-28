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
        # 테스트 환경은 FWS_PRELOAD_TRANSLATION_MODEL을 켜지 않으므로 꺼진 채로
        # 응답해야 한다. /health가 응답한다는 사실 자체가 lifespan startup이
        # 끝나 검색이 가능한 상태라는 뜻이고, 이 값은 번역 모델을 실제로
        # 미리 태웠는지만 별도로 알려준다.
        assert health.json()["translation_preloaded"] is False

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


def test_evaluation_endpoints_return_real_measured_data():
    # frontend 브랜치(backend/app/main.py)에서 이식(2026-08-28). 응답 형식은
    # 원본과 동일하게 유지한다. 관리자 대시보드가 호출하는 두 엔드포인트가
    # 실제 결과 파일로 200을 반환하는지, 측정되지 않은 지표는 추정하지 않고
    # null/빈 목록으로 나오는지 확인한다.
    with TestClient(app) as client:
        summary = client.get("/evaluation/summary")
        assert summary.status_code == 200
        assert set(summary.json()) == {
            "text_search", "multimodal_test", "multimodal_validation", "illustration_test",
        }

        metrics = client.get("/evaluation/metrics")
        assert metrics.status_code == 200
        payload = metrics.json()

        # 실측된 test/validation recall은 실제 값이 나와야 한다.
        datasets = {row["dataset"]: row for row in payload["quality_sets"]}
        assert datasets["multimodal_test"]["query_count"] == 40
        assert 0 < datasets["multimodal_test"]["recall_at_1"] <= 1
        assert datasets["multimodal_validation"]["image_weight"] == 0.4

        # 결과 파일에 없는 지표(nDCG)는 추정하지 않고 null로 나와야 한다.
        assert datasets["multimodal_test"]["ndcg"] is None

        # 쿼리 로그·이력 파일이 없으므로 로그 의존 지표는 null/빈 목록이어야
        # 한다 — 파일이 없다고 500이 나거나 값을 추정해서 채우면 안 된다.
        assert payload["zero_result_rate"] is None
        assert payload["average_latency_ms"] is None
        assert payload["trend"] == []
        assert payload["failed_queries"] == []
        assert payload["by_dimension"] == {
            "weapon_category": {}, "primary_color": {}, "elements": {},
        }

        # 가중치 스윕에 실제로 있는 지점(텍스트 전용 0.0, 선택된 0.4)은 값이
        # 채워지고, 스윕에 없는 지점(이미지 전용 1.0)은 null이어야 한다.
        modes = {row["key"]: row for row in payload["mode_comparison"]}
        assert modes["image"]["image_weight"] is None
        assert modes["text"]["image_weight"] == 0.0
        assert modes["multimodal"]["image_weight"] == 0.4
        assert modes["multimodal"]["recall"]["1"] is not None


def test_images_endpoint_serves_only_final_bundle_files():
    # 디렉터리를 통째로 공개하면 최종 번들에 없는 작업 파일까지 함께 노출된다.
    # 그래서 메타데이터에 실린 것만 허용 목록으로 제공한다.
    with TestClient(app) as client:
        assert len(app.state.image_files) == 1391
        served = client.get("/images/illustration/asset_001572.png")
        blocked = client.get("/images/pixel_art/asset_999999.png")
        # `../`는 클라이언트가 정규화해 서버까지 오지 않을 수 있으므로
        # 인코딩된 형태로 라우트가 직접 받도록 한다.
        traversals = [
            client.get("/images/%2e%2e/%2e%2e/data/metadata/final_search_assets.jsonl"),
            client.get("/images/pixel_art/%2e%2e/%2e%2e/metadata/final_search_assets.jsonl"),
        ]

    assert served.status_code == 200
    assert blocked.status_code == 404
    assert [response.status_code for response in traversals] == [404, 404]
