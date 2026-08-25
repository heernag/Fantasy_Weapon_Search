from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from pathlib import Path

from app.main import app
from app.main import form_filters
from app.schemas import SearchFilters


ROOT = Path(__file__).resolve().parents[1]


def test_multipart_filters_use_final_contract():
    filters = form_filters(
        visual_style="pixel_art",
        category="sword",
        subcategory="longsword",
        primary_color="blue",
        grade="legendary",
        colors="blue,gold",
        materials="steel,gold",
        elements="ice",
        shape_tags="bladed,enchanted",
    )

    assert filters.model_dump() == {
        "visual_style": "pixel_art",
        "category": "sword",
        "subcategory": "longsword",
        "primary_color": "blue",
        "grade": "legendary",
        "colors": ["blue", "gold"],
        "elements": ["ice"],
        "materials": ["steel", "gold"],
        "shape_tags": ["bladed", "enchanted"],
    }


def test_get_and_post_text_search_share_final_contract():
    with TestClient(app) as client:
        get_response = client.get(
            "/search/text",
            params={"query": "fire arrow", "top_k": 2, "category": "arrow"},
        )
        post_response = client.post(
            "/search/text",
            json={"query": "fire arrow", "top_k": 2, "filters": {"category": "arrow"}},
        )

    assert get_response.status_code == 200
    assert post_response.status_code == 200
    assert [row["asset_id"] for row in get_response.json()["results"]] == [
        row["asset_id"] for row in post_response.json()["results"]
    ]
    for payload in (get_response.json(), post_response.json()):
        assert payload["search_type"] == "text"
        assert payload["query_type"] == "text"
        assert payload["query_text"] == "fire arrow"
        assert payload["translated_text"] is None


def test_post_text_search_rejects_unknown_filter():
    with TestClient(app) as client:
        response = client.post(
            "/search/text",
            json={"query": "sword", "filters": {"unknown": "x"}},
        )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        ({"query": "   "}, "query"),
        ({"query": "sword", "top_k": 0}, "top_k"),
    ],
)
def test_post_text_search_uses_handoff_status_for_invalid_input(payload, expected_detail):
    with TestClient(app) as client:
        response = client.post("/search/text", json=payload)

    assert response.status_code == 400
    assert expected_detail in str(response.json()["detail"])


def test_original_design_filter_names_are_supported():
    filters = SearchFilters(
        color=["gold", "red"],
        element="fire",
        handedness="two_handed",
        style="medieval",
    )

    assert filters.canonical_colors() == ["gold", "red"]
    assert filters.canonical_elements() == ["fire"]
    assert filters.handedness == "two_handed"
    assert filters.style == "medieval"


def test_conflicting_original_and_extended_filter_names_are_rejected():
    with pytest.raises(ValidationError, match="color.*colors"):
        SearchFilters(color=["gold"], colors=["blue"])

    with pytest.raises(ValidationError, match="element.*elements"):
        SearchFilters(element="fire", elements=["ice"])


def test_equivalent_original_and_extended_filter_sets_are_allowed():
    filters = SearchFilters(
        color=["Gold", "red"],
        colors=["RED", "gold"],
        element="Fire",
        elements=["fire"],
    )

    assert filters.canonical_colors() == ["RED", "gold"]
    assert filters.canonical_elements() == ["fire"]


def test_filter_inventory_exposes_original_and_extended_names():
    with TestClient(app) as client:
        response = client.get("/filters")

    assert response.status_code == 200
    payload = response.json()
    for key in (
        "color", "colors", "element", "elements", "style", "handedness", "visual_style"
    ):
        assert key in payload
    assert payload["color"] == payload["colors"]
    assert payload["element"] == payload["elements"]


def test_filter_coverage_is_served_separately_from_filter_values():
    with TestClient(app) as client:
        values = client.get("/filters")
        coverage = client.get("/filters/coverage")

    assert values.status_code == coverage.status_code == 200
    # 모양이 다른 자료라 /filters 안에 섞지 않는다.
    assert "coverage" not in values.json()
    assert coverage.json()["elements"] == {"assets_with_value": 274, "total_assets": 1391}


def test_get_text_search_applies_original_design_filter_names():
    with TestClient(app) as client:
        response = client.get(
            "/search/text",
            params={"query": "fire arrow", "top_k": 3, "color": "orange", "element": "fire"},
        )

    assert response.status_code == 200
    for hit in response.json()["results"]:
        assert "orange" in hit["metadata"]["colors"]
        assert "fire" in hit["metadata"]["elements"]


def test_get_text_search_accepts_document_filter_notation():
    # 초기 설계 문서 규격의 `two-handed`와 대문자 표기로 요청해도 최종 데이터의
    # `two_handed`/`sword`와 같은 결과가 나와야 한다.
    with TestClient(app) as client:
        response = client.get(
            "/search/text",
            params={
                "query": "fantasy sword",
                "top_k": 3,
                "category": "Sword",
                "handedness": "two-handed",
            },
        )

    assert response.status_code == 200
    assert response.json()["results"]
    for hit in response.json()["results"]:
        assert hit["metadata"]["category"] == "sword"
        assert hit["metadata"]["handedness"] == "two_handed"


def test_get_text_search_rejects_unknown_parameter():
    # AI_SEARCH_API_HANDOFF_KO.md 10절: 지원하지 않는 필터는 400으로 돌려준다.
    with TestClient(app) as client:
        response = client.get(
            "/search/text",
            params={"query": "sword", "categoryy": "sword"},
        )

    assert response.status_code == 400
    assert "categoryy" in response.json()["detail"]


def test_image_search_rejects_unknown_form_field():
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client, image_path.open("rb") as handle:
        response = client.post(
            "/search/image",
            files={"image": (image_path.name, handle, "image/png")},
            data={"colours": "blue"},
        )

    assert response.status_code == 400
    assert "colours" in response.json()["detail"]


def test_text_search_pages_without_repeating_results():
    # Advanced 과제 주제 #2의 세부 과업: 리턴된 문서 페이징.
    with TestClient(app) as client:
        first = client.get("/search/text", params={"query": "fire arrow", "top_k": 3})
        second = client.get(
            "/search/text", params={"query": "fire arrow", "top_k": 3, "offset": 3}
        )
        combined = client.get("/search/text", params={"query": "fire arrow", "top_k": 6})

    assert first.status_code == second.status_code == 200
    assert first.json()["offset"] == 0
    assert second.json()["offset"] == 3

    first_ids = [row["asset_id"] for row in first.json()["results"]]
    second_ids = [row["asset_id"] for row in second.json()["results"]]
    combined_ids = [row["asset_id"] for row in combined.json()["results"]]

    assert not set(first_ids) & set(second_ids)
    assert first_ids + second_ids == combined_ids
    # 전체 후보 수를 함께 주므로 프론트엔드가 마지막 페이지를 계산할 수 있다.
    assert first.json()["candidate_count"] >= len(combined_ids)


def test_ranked_window_matches_the_search_service_limit():
    # API 경계값은 MAX_RANKED_RESULTS 하나에서 나온다. 검색 서비스가 다른 상한을
    # 쓰기 시작하면 페이지 요청이 서비스 단에서 거절되므로 함께 확인한다.
    import pytest as _pytest

    from app.schemas import MAX_RANKED_RESULTS
    from src.retrieval.search_service import WeaponSearchService

    WeaponSearchService._validate_top_k(MAX_RANKED_RESULTS)
    with _pytest.raises(ValueError):
        WeaponSearchService._validate_top_k(MAX_RANKED_RESULTS + 1)


def test_page_beyond_ranked_window_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/search/text", json={"query": "sword", "top_k": 10, "offset": 95}
        )

    assert response.status_code == 400
    assert "offset" in str(response.json()["detail"])


def test_search_hit_exposes_official_metadata_attributes():
    # 초기 설계 문서 규격의 handedness/style을 결과에서 바로 읽을 수 있어야 한다.
    with TestClient(app) as client:
        response = client.get("/search/text", params={"query": "fantasy sword", "top_k": 3})

    assert response.status_code == 200
    for hit in response.json()["results"]:
        assert hit["handedness"] == hit["metadata"]["handedness"]
        assert hit["style"] == hit["metadata"]["style"]


def test_legacy_filter_aliases_behave_the_same_on_get_and_post():
    # `categories`/`styles`는 POST 본문에서만 통하고 GET에서는 무시되던 호환 입력이다.
    # 네 엔드포인트가 같은 필터 모델을 쓰도록 GET과 폼에서도 받는다.
    with TestClient(app) as client:
        post = client.post(
            "/search/text",
            json={"query": "fire arrow", "top_k": 3, "filters": {"categories": ["arrow"]}},
        )
        get = client.get(
            "/search/text",
            params={"query": "fire arrow", "top_k": 3, "categories": "arrow"},
        )

    assert post.status_code == get.status_code == 200
    assert [row["asset_id"] for row in post.json()["results"]] == [
        row["asset_id"] for row in get.json()["results"]
    ]
    for hit in get.json()["results"]:
        assert hit["category"] == "arrow"


def test_multi_valued_attributes_stay_lists_in_the_response():
    # [의도적 결정] 메타데이터 규격의 단일 문자열 표기를 따르지 않는다.
    # 값이 둘 이상인 에셋에서 두 번째부터 사라지는 것을 막기 위해서다.
    # 규격 쪽으로 돌아가기로 정하면 app/schemas.py의 SearchHit 주석을 따른다.
    with TestClient(app) as client:
        response = client.get("/search/text", params={"query": "fire sword", "top_k": 5})

    assert response.status_code == 200
    for hit in response.json()["results"]:
        assert isinstance(hit["element"], list)
        assert isinstance(hit["color"], list)
        assert hit["element"] == hit["metadata"]["elements"]
        assert hit["color"] == hit["metadata"]["colors"]


def test_get_text_search_returns_400_for_filter_conflicts():
    # 필터 충돌은 pydantic 예외로 올라오므로 변환하지 않으면 500이 된다.
    with TestClient(app) as client:
        alias = client.get(
            "/search/text",
            params={"query": "sword", "category": "sword", "categories": "arrow"},
        )
        plural = client.get(
            "/search/text",
            params={"query": "sword", "color": "gold", "colors": "blue"},
        )

    assert alias.status_code == 400
    assert plural.status_code == 400


def test_blank_filter_value_is_rejected_the_same_way_on_get_and_post():
    # 쿼리스트링과 JSON은 "안 보냄"과 "빈 값"이 구분되므로 같은 응답을 준다.
    # 폼은 미입력 필드가 빈 문자열로 도착해 구분할 수 없어 무시한다.
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client:
        get = client.get("/search/text", params={"query": "sword", "category": ""})
        post = client.post("/search/text", json={"query": "sword", "filters": {"category": ""}})
        with image_path.open("rb") as handle:
            form = client.post(
                "/search/image",
                files={"image": (image_path.name, handle, "image/png")},
                data={"category": "", "top_k": "2"},
            )

    assert get.status_code == 400
    assert post.status_code == 400
    assert form.status_code == 200


def test_root_url_leads_to_the_api_docs():
    # 배너가 안내하는 주소를 브라우저로 열었을 때 404가 나오면 안 된다.
    with TestClient(app) as client:
        redirect = client.get("/", follow_redirects=False)
        followed = client.get("/")

    assert redirect.status_code in (302, 307)
    assert redirect.headers["location"] == "/docs"
    assert followed.status_code == 200


def test_catastrophic_mistranslations_are_bypassed():
    # 번역기가 "창"을 Windows로 바꾸는 등 뜻이 아예 달라지는 용어만 우회한다.
    with TestClient(app) as client:
        spear = client.get("/search/text", params={"query": "창", "top_k": 5}).json()
        shuriken = client.get("/search/text", params={"query": "표창", "top_k": 5}).json()

    assert spear["rewritten_query"] == "spear"
    assert shuriken["rewritten_query"] == "shuriken"
    # 응답에는 사용자가 보낸 원문이 그대로 실려야 한다.
    assert spear["query_text"] == "창"
    # 영어로 다시 썼으므로 번역 단계를 거치지 않는다.
    assert spear["translated_text"] is None
    assert sum(1 for hit in spear["results"] if hit["category"] == "spear") >= 3
    assert sum(1 for hit in shuriken["results"] if hit["category"] == "shuriken") >= 3


def test_queries_without_mistranslated_terms_are_left_alone():
    # 어색한 문장이나 미묘한 뉘앙스는 손대지 않는다. 번역 경로를 그대로 쓴다.
    with TestClient(app) as client:
        payload = client.get("/search/text", params={"query": "파란 검", "top_k": 3}).json()

    assert payload["rewritten_query"] is None
    assert payload["query_text"] == "파란 검"
    assert payload["translated_text"]


def test_multipart_filter_alias_conflicts_are_rejected():
    with pytest.raises(ValidationError, match="color.*colors"):
        form_filters(colors="blue", color="gold")


def test_image_endpoint_returns_400_for_filter_alias_conflicts():
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client, image_path.open("rb") as handle:
        response = client.post(
            "/search/image",
            files={"image": (image_path.name, handle, "image/png")},
            data={"colors": "blue", "color": "gold"},
        )

    assert response.status_code == 400
    assert "color" in response.json()["detail"]
    assert "colors" in response.json()["detail"]


def test_openapi_exposes_original_and_extended_contracts():
    schema = app.openapi()
    filters = schema["components"]["schemas"]["SearchFilters"]["properties"]
    hits = schema["components"]["schemas"]["SearchHit"]["properties"]

    for name in (
        "color", "colors", "element", "elements", "style", "visual_style", "handedness"
    ):
        assert name in filters
    for name in (
        "result_text", "image_path", "image_url", "color", "colors", "element", "elements",
        "source", "source_url", "handedness", "style"
    ):
        assert name in hits


def test_multimodal_rejects_weights_that_do_not_sum_to_one():
    # 합이 1이 아닌 값을 조용히 재조정하면 응답의 가중치가 요청과 달라진다.
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client, image_path.open("rb") as handle:
        response = client.post(
            "/search/multimodal",
            files={"image": (image_path.name, handle, "image/png")},
            data={"query": "sword", "image_weight": "0.7"},
        )

    assert response.status_code == 400
    assert "1" in response.json()["detail"]


def test_multipart_search_uses_handoff_status_for_invalid_top_k_and_weights():
    image_path = ROOT / "data/processed/pixel_art/asset_000057.png"
    with TestClient(app) as client:
        with image_path.open("rb") as handle:
            image_response = client.post(
                "/search/image",
                files={"image": (image_path.name, handle, "image/png")},
                data={"top_k": "0"},
            )
        with image_path.open("rb") as handle:
            multimodal_response = client.post(
                "/search/multimodal",
                files={"image": (image_path.name, handle, "image/png")},
                data={"query": "sword", "image_weight": "0", "text_weight": "0"},
            )

    assert image_response.status_code == 400
    assert multimodal_response.status_code == 400
