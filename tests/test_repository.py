from pathlib import Path

import pytest

from app.official_search import OfficialSearchAdapter
from app.repository import AssetRepository
from app.schemas import SearchFilters
from src.retrieval import search_service


ROOT = Path(__file__).resolve().parents[1]


def applied(repo: AssetRepository, **kwargs) -> dict:
    """API 경계가 실제로 검색 서비스에 넘기는 필터를 만든다."""
    return repo.canonicalize(OfficialSearchAdapter.filter_dict(SearchFilters(**kwargs)))


def matches(asset: dict, filters: dict) -> bool:
    """검색 결과를 실제로 결정하는 판정기로 확인한다."""
    return search_service.WeaponSearchService._matches_filters(asset, filters)


def test_metadata_loads_and_ids_are_unique():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    assert len(repo.assets) == 1391
    assert len(repo.by_id) == 1391


def test_filters_match_known_asset():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    asset = repo.get("asset_000057")
    assert matches(asset, applied(repo, categories=["arrow"], elements=["fire"]))
    assert not matches(asset, applied(repo, categories=["sword"]))


def test_final_scalar_filters_match_known_asset():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    asset = repo.get("asset_000057")

    filters = applied(
        repo,
        visual_style=asset["visual_style"],
        category=asset["category"],
        subcategory=asset["subcategory"],
        primary_color=asset["primary_color"],
        grade=asset["grade"],
    )

    assert matches(asset, filters)


def test_list_filter_requires_every_requested_value():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    asset = repo.get("asset_000057")
    assert asset["colors"] == ["orange", "yellow", "white"]

    assert matches(asset, applied(repo, colors=["orange", "yellow"]))
    assert not matches(asset, applied(repo, colors=["orange", "blue"]))


def test_original_and_extended_filters_match_the_same_assets():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    original = applied(repo, color=["orange"], element="fire")
    extended = applied(repo, colors=["orange"], elements=["fire"])

    assert [asset["asset_id"] for asset in repo.assets if matches(asset, original)] == [
        asset["asset_id"] for asset in repo.assets if matches(asset, extended)
    ]


def test_filter_values_match_regardless_of_notation():
    # 초기 설계 문서의 메타데이터 규격은 `two-handed`로 적혀 있고 최종 데이터는
    # `two_handed`로 저장되어 있다. 두 표기 모두 같은 에셋을 찾아야 한다.
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    stored = applied(repo, handedness="two_handed", category="sword")
    document = applied(repo, handedness="two-handed", category="Sword")

    assert document == stored
    assert [asset["asset_id"] for asset in repo.assets if matches(asset, document)] == [
        asset["asset_id"] for asset in repo.assets if matches(asset, stored)
    ]


def test_unknown_filter_value_is_left_untouched():
    # 표기 정규화는 실제 존재하는 값만 바꾸고, 오탈자는 그대로 넘겨 기존의
    # "결과 없음" 응답을 유지한다.
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    assert applied(repo, category="nonexistent-weapon") == {"category": "nonexistent-weapon"}


def test_filter_fields_stay_in_sync_with_search_service():
    # 필터 어휘는 저장소가, 판정은 검색 서비스가 담당하므로 두 목록이
    # 어긋나면 정규화되지 않은 필터가 그대로 검색에 전달된다.
    assert set(AssetRepository.SCALAR_FILTER_FIELDS) == search_service.SCALAR_FILTERS
    assert set(AssetRepository.LIST_FILTER_FIELDS) == search_service.LIST_FILTERS


def test_unknown_filter_is_rejected():
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        SearchFilters.model_validate({"unknown": "value"})


def test_filter_inventory_has_expected_categories():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    categories = {item["value"]: item["count"] for item in repo.filter_values()["category"]}
    # 최종 1,391개 메타데이터의 대표 분포를 고정해 누락된 스타일 묶음이나
    # 잘못된 메타데이터 파일을 서버가 읽는 회귀를 빠르게 발견한다.
    assert categories["sword"] == 500
    assert categories["shield"] == 422


def test_filter_inventory_uses_final_contract_names():
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")

    assert set(repo.filter_values()) == {
        "visual_style",
        "category",
        "subcategory",
        "primary_color",
        "grade",
        "color",
        "colors",
        "materials",
        "element",
        "elements",
        "shape_tags",
        "style",
        "handedness",
    }

    assert repo.filter_values()["color"] == repo.filter_values()["colors"]
    assert repo.filter_values()["element"] == repo.filter_values()["elements"]


def test_filter_values_keeps_one_shape_for_every_field():
    # 필터 UI가 키를 순회하므로 값 목록이 아닌 항목이 섞이면 안 된다.
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    for field, values in repo.filter_values().items():
        assert isinstance(values, list), field
        assert all(set(row) == {"value", "count"} for row in values), field


def test_filter_coverage_reports_partially_tagged_attributes():
    # elements는 1,391개 중 274개에만 채워져 있어 필터를 거는 순간 후보가
    # 20%로 줄어든다. 프론트엔드가 이 사실을 표시할 수 있어야 한다.
    repo = AssetRepository(ROOT / "data/metadata/final_search_assets.jsonl")
    coverage = repo.filter_coverage()

    assert coverage["elements"] == {"assets_with_value": 274, "total_assets": 1391}
    assert coverage["element"] == coverage["elements"]
    assert coverage["category"] == {"assets_with_value": 1391, "total_assets": 1391}


def test_duplicate_asset_ids_are_rejected(tmp_path):
    metadata = tmp_path / "assets.jsonl"
    metadata.write_text(
        '{"asset_id":"duplicate"}\n{"asset_id":"duplicate"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="중복 asset_id"):
        AssetRepository(metadata)
