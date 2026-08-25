import json
import time

from PIL import Image

from app.config import get_settings
from app.repository import AssetRepository
from app.schemas import SearchFilters


class FakeOfficialService:
    def __init__(self):
        self.calls = []

    def search_text(self, text, top_k=10, filters=None):
        self.calls.append(("text", text, top_k, filters))
        return {
            "search_type": "text",
            "query_text": text,
            "translated_text": None,
            "candidate_count": 1,
            "results": [{"asset_id": "asset_000057", "score": 0.9}],
        }

    def search_image(
        self, image, top_k=10, filters=None, include_self=False,
        excluded_asset_ids=None,
    ):
        self.calls.append(
            ("image", image, top_k, filters, include_self, excluded_asset_ids)
        )
        return {
            "search_type": "image",
            "candidate_count": 1,
            "results": [{"asset_id": "asset_000057", "score": 0.8}],
        }

    def search_multimodal(
        self, image, text, top_k=10, filters=None, image_weight=0.4,
        excluded_asset_ids=None,
    ):
        self.calls.append(
            ("multimodal", image, text, top_k, filters, image_weight, excluded_asset_ids)
        )
        return {
            "search_type": "multimodal",
            "query_text": text,
            "translated_text": "fire sword",
            "image_weight": image_weight,
            "text_weight": 1 - image_weight,
            "candidate_count": 1,
            "results": [{
                "asset_id": "asset_000057",
                "score": 0.7,
                "combined_score": 0.7,
                "image_score": 0.8,
                "text_score": 0.6,
            }],
        }


class PagingOfficialService(FakeOfficialService):
    """순위를 여러 개 돌려줘 페이지 잘라내기를 확인하기 위한 대역."""

    def __init__(self, asset_ids):
        super().__init__()
        self.asset_ids = asset_ids

    def search_text(self, text, top_k=10, filters=None):
        self.calls.append(("text", text, top_k, filters))
        return {
            "search_type": "text",
            "query_text": text,
            "translated_text": None,
            "candidate_count": len(self.asset_ids),
            "results": [
                {"asset_id": asset_id, "score": 0.9 - index / 10}
                for index, asset_id in enumerate(self.asset_ids[:top_k])
            ],
        }


def test_fastapi_factory_constructs_official_adapter_service(monkeypatch):
    import app.main as main

    created = []

    class RecordingService:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setattr(main, "WeaponSearchService", RecordingService, raising=False)

    service = main.create_search_service(get_settings())

    assert isinstance(service, RecordingService)
    assert len(created) == 1
    assert created[0]["root"] == get_settings().project_root


def test_official_adapter_preserves_response_and_log_contract(tmp_path):
    from app.official_search import OfficialSearchAdapter

    settings = get_settings()
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    official = FakeOfficialService()
    log_path = tmp_path / "search.jsonl"
    adapter = OfficialSearchAdapter(official, repository, log_path)
    filters = SearchFilters(
        color=["orange"], element="fire", style="medieval", handedness="two_handed"
    )

    response = adapter.search_text(
        "fire arrow",
        top_k=1,
        offset=0,
        filters=filters,
        request_started=time.perf_counter(),
        service_version="test-v1",
    )

    assert official.calls[0][3] == {
        "colors": ["orange"],
        "elements": ["fire"],
        "style": "medieval",
        "handedness": "two_handed",
    }
    assert response["query_type"] == "text"
    assert response["top_k"] == 1
    assert response["elapsed_ms"] >= response["search_elapsed_ms"] >= 0
    hit = response["results"][0]
    assert hit["metadata"]["asset_id"] == "asset_000057"
    assert hit["image_url"].startswith("/images/")
    assert hit["result_text"] == (hit["caption_ko"] or hit["caption_en"])
    assert hit["color"] == hit["colors"]
    assert hit["element"] == hit["elements"]
    assert hit["source"] == hit["source_url"]

    logged = json.loads(log_path.read_text(encoding="utf-8"))
    assert logged["query_type"] == "text"
    assert logged["status_code"] == 200
    assert logged["service_version"] == "test-v1"
    assert logged["offset"] == 0


def test_official_adapter_pages_through_ranked_results(tmp_path):
    from app.official_search import OfficialSearchAdapter

    settings = get_settings()
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    official = PagingOfficialService(["asset_000057", "asset_001332", "asset_001572"])
    adapter = OfficialSearchAdapter(official, repository, tmp_path / "search.jsonl")

    page = adapter.search_text(
        "fire arrow",
        top_k=2,
        offset=1,
        filters=SearchFilters(),
        request_started=time.perf_counter(),
        service_version="test-v1",
    )

    # 서비스에는 offset + top_k개를 요청하고, 응답은 그 뒤쪽 페이지만 담는다.
    assert official.calls[0][2] == 3
    assert [hit["asset_id"] for hit in page["results"]] == ["asset_001332", "asset_001572"]
    assert page["offset"] == 1
    assert page["top_k"] == 2


def test_official_adapter_forwards_upload_self_exclusion(tmp_path):
    from app.official_search import OfficialSearchAdapter

    settings = get_settings()
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    official = FakeOfficialService()
    adapter = OfficialSearchAdapter(official, repository, tmp_path / "search.jsonl")

    adapter.search_image(
        Image.new("RGB", (2, 2)),
        detail="query.png",
        top_k=1,
        offset=0,
        filters=SearchFilters(),
        excluded_asset_ids={"asset_000057"},
        include_self=False,
        request_started=time.perf_counter(),
        service_version="test-v1",
    )

    assert official.calls[0][-1] == {"asset_000057"}


def test_production_has_no_duplicate_model_or_ranking_path():
    main_source = (get_settings().project_root / "app/main.py").read_text(encoding="utf-8")
    assert "app.adapter_embeddings" not in main_source
    assert "app.model_service" not in main_source
    assert "FaissVectorStore" not in main_source
    assert "from app.service import" not in main_source
