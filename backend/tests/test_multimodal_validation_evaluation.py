from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_multimodal_validation_evaluation import build_candidates, build_concepts  # noqa: E402


def _asset(
    asset_id: str,
    *,
    color: str,
    elements: list[str],
    materials: list[str],
    style_variant: str,
) -> dict:
    return {
        "asset_id": asset_id,
        "category": "sword",
        "subcategory": "longsword",
        "primary_color": color,
        "elements": elements,
        "materials": materials,
        "style_variant": style_variant,
        "processed_file": f"data/processed/pixel_art/{asset_id}.png",
    }


def test_concepts_only_use_validation_assets_and_keep_weapon_kind() -> None:
    rows = [
        _asset("asset_gray", color="gray", elements=["fire"], materials=["steel"], style_variant="classic_pixel_art"),
        _asset("asset_blue", color="blue", elements=["ice"], materials=["wood"], style_variant="rendered_pixel_icon"),
        _asset("asset_gold", color="gold", elements=["lightning"], materials=["bronze"], style_variant="classic_pixel_art"),
    ]

    concepts = build_concepts(rows, max_concepts_per_type=1)

    assert {concept["query_type"] for concept in concepts} == {
        "color_change",
        "element_change",
        "material_change",
        "style_change",
    }
    for concept in concepts:
        assert concept["source"]["asset_id"] in {row["asset_id"] for row in rows}
        assert set(concept["relevant_ids"]) <= {row["asset_id"] for row in rows}
        assert concept["preserve_filters"] == {"category": "sword", "subcategory": "longsword"}
        assert concept["source"]["asset_id"] not in concept["relevant_ids"]


def test_style_change_uses_style_variant_not_visual_style() -> None:
    rows = [
        _asset("asset_classic", color="gray", elements=[], materials=["steel"], style_variant="classic_pixel_art"),
        _asset("asset_rendered", color="blue", elements=[], materials=["steel"], style_variant="rendered_pixel_icon"),
    ]

    style_concepts = build_candidates(rows, "style_change", "style_variant")

    assert style_concepts
    assert all(concept["target_filters"].keys() == {"style_variant"} for concept in style_concepts)


def test_generated_validation_files_stay_inside_validation_split() -> None:
    import json

    validation_ids = {
        json.loads(line)["asset_id"]
        for line in (ROOT / "data/splits/validation.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }
    queries = [
        json.loads(line)
        for line in (ROOT / "data/evaluation/multimodal_validation_queries.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    truths = {
        row["query_id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "data/evaluation/multimodal_validation_ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }

    assert len(queries) == len(truths) == 80
    assert {query["query_type"] for query in queries} == {
        "color_change",
        "element_change",
        "material_change",
        "style_change",
    }
    for query in queries:
        assert query["candidate_split"] == "validation"
        assert query["query_image_id"] in validation_ids
        assert set(query["preserve_filters"]) == {"category", "subcategory"}
        truth = truths[query["query_id"]]
        assert truth["candidate_split"] == "validation"
        assert set(truth["relevant_asset_ids"]) <= validation_ids
