from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_manifest_hash_matches_declared_metadata_file() -> None:
    manifest_path = ROOT / "data/metadata/final_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata_path = ROOT / manifest["source_metadata"]["path"]

    assert hashlib.sha256(metadata_path.read_bytes()).hexdigest() == (
        manifest["source_metadata"]["sha256"]
    )


def test_sync_splits_ignores_non_split_jsonl(tmp_path, monkeypatch) -> None:
    import scripts.finalize_dataset as finalize_dataset

    split_dir = tmp_path / "splits"
    split_dir.mkdir()
    canonical = {"asset_id": "asset_current", "category": "sword"}
    for name in ("train", "validation", "test"):
        (split_dir / f"{name}.jsonl").write_text(
            '{"asset_id":"asset_current"}\n', encoding="utf-8"
        )
    unrelated = split_dir / "split_manifest.jsonl"
    unrelated.write_text('{"asset_id":"asset_removed"}\n', encoding="utf-8")
    monkeypatch.setattr(finalize_dataset, "SPLIT_DIRECTORIES", {"pixel_art": split_dir})

    finalize_dataset.sync_splits({"asset_current": canonical})

    assert json.loads(unrelated.read_text(encoding="utf-8"))["asset_id"] == "asset_removed"
sys.path.insert(0, str(ROOT / "scripts"))

import finalize_dataset
import rebuild_ground_truth_and_manifest


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def test_refresh_split_summary_uses_current_jsonl_counts_after_regrouping(tmp_path: Path) -> None:
    split_dir = tmp_path / "illustration"
    split_dir.mkdir()
    _write_jsonl(split_dir / "train.jsonl", [{"asset_id": "asset_1"}, {"asset_id": "asset_2"}])
    _write_jsonl(split_dir / "validation.jsonl", [{"asset_id": "asset_3"}])
    _write_jsonl(split_dir / "test.jsonl", [{"asset_id": "asset_4"}, {"asset_id": "asset_5"}, {"asset_id": "asset_6"}])
    summary_path = split_dir / "split_summary.json"
    summary_path.write_text(
        json.dumps({"total": 284, "counts": {"train": 230, "validation": 27, "test": 27}}),
        encoding="utf-8",
    )

    summary = finalize_dataset.refresh_split_summary(summary_path, split_dir, "illustration")

    assert summary["counts"] == {"train": 2, "validation": 1, "test": 3}
    assert summary["total"] == 6
    assert summary["overlap_count"] == 0


def test_refresh_evaluation_summary_recomputes_ground_truth_distribution(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.jsonl"
    _write_jsonl(
        ground_truth,
        [
            {"query_id": "q1", "relevant_asset_ids": ["asset_1"]},
            {"query_id": "q2", "relevant_asset_ids": ["asset_2", "asset_3", "asset_4"]},
        ],
    )
    summary_path = tmp_path / "evaluation_summary.json"
    summary_path.write_text(
        json.dumps({"candidate_asset_count": 112, "query_count": 160, "ground_truth": {"maximum_relevant_assets": 66}}),
        encoding="utf-8",
    )

    summary = finalize_dataset.refresh_evaluation_summary(
        summary_path,
        ground_truth,
        candidate_count=5,
        query_count=2,
        concept_count=1,
    )

    assert summary["candidate_asset_count"] == 5
    assert summary["query_count"] == 2
    assert summary["concept_count"] == 1
    assert summary["ground_truth"] == {
        "relevance": "binary",
        "minimum_relevant_assets": 1,
        "maximum_relevant_assets": 3,
        "average_relevant_assets": 2.0,
    }


def test_variant_leak_detection_groups_by_perceptual_hash_before_legacy_group_name(tmp_path: Path) -> None:
    split_dir = tmp_path / "illustration"
    split_dir.mkdir()
    _write_jsonl(
        split_dir / "train.jsonl",
        [{"asset_id": "asset_1", "variant_group": "legacy_group", "perceptual_hash": "same_hash"}],
    )
    _write_jsonl(split_dir / "validation.jsonl", [])
    _write_jsonl(
        split_dir / "test.jsonl",
        [{"asset_id": "asset_2", "perceptual_hash": "same_hash"}],
    )

    summary = finalize_dataset.refresh_split_summary(split_dir / "split_summary.json", split_dir, "illustration")

    assert summary["perceptual_hash_groups"] == 1
    assert summary["group_leaks"] == 1


def test_handoff_manifest_uses_handoff_relative_split_paths(tmp_path: Path) -> None:
    manifest_path = tmp_path / "final_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_metadata": {},
                "splits": {"pixel_art": {"files": {"train": {"path": "data/splits/train.jsonl"}}}},
            }
        ),
        encoding="utf-8",
    )

    finalize_dataset.refresh_manifest(
        manifest_path,
        [],
        source_metadata_path="final_search_assets_pretty.json",
        split_path_prefix="splits",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_metadata"]["path"] == "final_search_assets_pretty.json"
    assert manifest["splits"]["pixel_art"]["files"]["train"]["path"] == "splits/pixel_art/train.jsonl"


def test_root_manifest_uses_root_pixel_art_split_paths(tmp_path: Path) -> None:
    manifest_path = tmp_path / "final_manifest.json"
    manifest_path.write_text(json.dumps({"source_metadata": {}, "splits": {}}), encoding="utf-8")

    finalize_dataset.refresh_manifest(
        manifest_path,
        [],
        source_metadata_path="data/metadata/final_search_assets_pretty.json",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["splits"]["pixel_art"]["files"]["train"]["path"] == "data/splits/train.jsonl"


def test_current_release_documents_describe_regenerated_split_counts() -> None:
    repo = Path(__file__).resolve().parents[1]

    split_readme = (repo / "data/splits/README.md").read_text(encoding="utf-8")
    illustration_guide = (repo / "data/evaluation/ILLUSTRATION_EVALUATION_GUIDE_KO.md").read_text(encoding="utf-8")
    rendered_policy = (repo / "reports/RENDERED_ICON_SPLIT_POLICY_KO.md").read_text(encoding="utf-8")

    assert "| 일러스트 | 229 | 18 | 37 | 284 |" in split_readme
    assert "| 렌더 아이콘 | 121 | 15 | 14 | 150 |" in split_readme
    assert "test` split 37개" in illustration_guide
    assert "질의 100개" in illustration_guide
    assert "train 121개, validation 15개, test 14개" in rendered_policy


def test_current_pixel_art_split_summary_matches_release_jsonl() -> None:
    repo = Path(__file__).resolve().parents[1]
    split_dir = repo / "data/splits"
    summary = json.loads((split_dir / "split_summary.json").read_text(encoding="utf-8"))

    expected_counts = {
        name: len(
            [
                line
                for line in (split_dir / f"{name}.jsonl").read_text(encoding="utf-8-sig").splitlines()
                if line.strip()
            ]
        )
        for name in ("train", "validation", "test")
    }

    assert summary["counts"] == expected_counts
    assert summary["total"] == sum(expected_counts.values())


def test_ground_truth_rebuild_also_refreshes_release_docs(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(rebuild_ground_truth_and_manifest, "jl", lambda _path: [])
    monkeypatch.setattr(rebuild_ground_truth_and_manifest, "rebuild_text", lambda *_: None)
    monkeypatch.setattr(rebuild_ground_truth_and_manifest, "rebuild_multimodal", lambda *_: None)
    monkeypatch.setattr(rebuild_ground_truth_and_manifest, "rebuild_illustration", lambda *_: None)
    monkeypatch.setattr(
        rebuild_ground_truth_and_manifest,
        "refresh_release_artifacts",
        lambda _meta: calls.append("artifacts"),
    )
    monkeypatch.setattr(
        rebuild_ground_truth_and_manifest,
        "refresh_release_docs",
        lambda: calls.append("docs"),
    )

    rebuild_ground_truth_and_manifest.main()

    assert calls == ["artifacts", "docs"]


def test_final_backend_handoff_names_one_authoritative_search_service() -> None:
    handoff = ROOT / "docs/BACKEND_VECTORDB_HANDOFF_KO.md"

    assert handoff.exists()
    text = handoff.read_text(encoding="utf-8")
    assert "from src.retrieval.search_service_adapter import WeaponSearchService" in text
    assert "src.retrieval.search_service.WeaponSearchService" in text
    assert "베이스라인" in text
    assert "storage/indexes/weapons.faiss" in text
    assert "storage/indexes/weapon_ids.json" in text
    assert "서버 시작 시 한 번" in text
    assert "CUSTOM_ADAPTER_HANDOFF_KO.md" in text
    assert "AI_SEARCH_API_HANDOFF_KO.md" in text
