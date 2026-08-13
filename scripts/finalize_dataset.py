"""Synchronize release-derived files from canonical metadata, splits, and evaluation JSONL."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/metadata/final_search_assets_pretty.json"
SPLIT_DIRECTORIES = {
    "pixel_art": ROOT / "data/splits",
    "illustration": ROOT / "data/splits/illustration",
    "rendered_icon": ROOT / "data/splits/rendered_icon",
}
SPLIT_NAMES = ("train", "validation", "test")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def split_counts(split_dir: Path) -> dict[str, int]:
    return {name: len(read_jsonl(split_dir / f"{name}.jsonl")) for name in SPLIT_NAMES}


def _split_rows(split_dir: Path) -> dict[str, list[dict[str, Any]]]:
    return {name: read_jsonl(split_dir / f"{name}.jsonl") for name in SPLIT_NAMES}


def _overlap_count(rows_by_split: dict[str, list[dict[str, Any]]]) -> int:
    ids_by_split = {name: {row["asset_id"] for row in rows} for name, rows in rows_by_split.items()}
    overlaps: set[str] = set()
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlaps.update(ids_by_split[left] & ids_by_split[right])
    return len(overlaps)


def _variant_group_summary(rows_by_split: dict[str, list[dict[str, Any]]]) -> tuple[int, int]:
    group_locations: dict[str, set[str]] = {}
    for split_name, rows in rows_by_split.items():
        for row in rows:
            # Regrouping uses exact perceptual hashes.  A partially populated legacy
            # variant_group must not hide a perceptual-hash leak across splits.
            group = row.get("perceptual_hash") or row.get("variant_group") or row["asset_id"]
            group_locations.setdefault(str(group), set()).add(split_name)
    return len(group_locations), sum(len(locations) > 1 for locations in group_locations.values())


def refresh_split_summary(summary_path: Path, split_dir: Path, style: str) -> dict[str, Any]:
    """Regenerate a split summary from its JSONL files, never from old summary values."""
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    rows_by_split = _split_rows(split_dir)
    counts = {name: len(rows) for name, rows in rows_by_split.items()}
    summary["counts"] = counts
    summary["total"] = sum(counts.values())
    summary["overlap_count"] = _overlap_count(rows_by_split)

    if style in {"illustration", "rendered_icon"}:
        perceptual_hash_groups, group_leaks = _variant_group_summary(rows_by_split)
        summary["perceptual_hash_groups"] = perceptual_hash_groups
        # Kept as a compatibility alias for older consumers; it now uses the
        # same exact perceptual-hash grouping as the leak check.
        summary["variant_groups"] = perceptual_hash_groups
        summary["group_leaks"] = group_leaks

    if style == "rendered_icon":
        summary.setdefault("dataset", "rendered_icon")
        summary.setdefault("policy", "separate_split")
        summary.setdefault("visual_style", "rendered_icon")
        summary.setdefault("seed", 20260812)
        summary.setdefault("ratios", {"train": 0.8, "validation": 0.1, "test": 0.1})
        summary["notes"] = "렌더 아이콘은 pixel_art 및 illustration split과 분리해 독립 검색·평가 대상으로 관리합니다."

    summary.setdefault("source_metadata", "data/metadata/final_search_assets_pretty.json")
    write_json(summary_path, summary)
    return summary


def refresh_split_summaries() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for style in ("illustration", "rendered_icon"):
        split_dir = SPLIT_DIRECTORIES[style]
        results[style] = refresh_split_summary(split_dir / "split_summary.json", split_dir, style)
    return results


def ground_truth_statistics(ground_truth_path: Path) -> dict[str, Any]:
    rows = read_jsonl(ground_truth_path)
    if not rows:
        raise ValueError(f"Ground truth is empty: {ground_truth_path}")
    relevant_counts = [len(row.get("relevant_asset_ids", [])) for row in rows]
    if not all(relevant_counts):
        raise ValueError(f"Ground truth contains an empty relevance list: {ground_truth_path}")
    return {
        "relevance": "binary",
        "minimum_relevant_assets": min(relevant_counts),
        "maximum_relevant_assets": max(relevant_counts),
        "average_relevant_assets": round(sum(relevant_counts) / len(relevant_counts), 3),
    }


def refresh_evaluation_summary(
    summary_path: Path,
    ground_truth_path: Path,
    *,
    candidate_count: int,
    query_count: int,
    concept_count: int | None = None,
    language_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Synchronize summary counts and relevance distribution with current JSONL files."""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["candidate_asset_count"] = candidate_count
    summary["query_count"] = query_count
    if concept_count is not None:
        summary["concept_count"] = concept_count
    if language_counts is not None:
        summary["language_counts"] = language_counts
    summary["ground_truth"] = ground_truth_statistics(ground_truth_path)
    write_json(summary_path, summary)
    return summary


def refresh_evaluation_summaries() -> dict[str, dict[str, Any]]:
    evaluation = ROOT / "data/evaluation"
    pixel_test_count = len(read_jsonl(SPLIT_DIRECTORIES["pixel_art"] / "test.jsonl"))
    illustration_test_count = len(read_jsonl(SPLIT_DIRECTORIES["illustration"] / "test.jsonl"))

    text_queries = read_jsonl(evaluation / "evaluation_queries.jsonl")
    multimodal_queries = read_jsonl(evaluation / "multimodal_queries.jsonl")
    illustration_queries = read_jsonl(evaluation / "illustration_evaluation_queries.jsonl")
    illustration_languages = {
        "ko": sum(row.get("language") == "ko" for row in illustration_queries),
        "en": sum(row.get("language") == "en" for row in illustration_queries),
    }

    return {
        "text": refresh_evaluation_summary(
            evaluation / "evaluation_summary.json",
            evaluation / "ground_truth.jsonl",
            candidate_count=pixel_test_count,
            query_count=len(text_queries),
        ),
        "multimodal": refresh_evaluation_summary(
            evaluation / "multimodal_evaluation_summary.json",
            evaluation / "multimodal_ground_truth.jsonl",
            candidate_count=pixel_test_count,
            query_count=len(multimodal_queries),
        ),
        "illustration": refresh_evaluation_summary(
            evaluation / "illustration_evaluation_summary.json",
            evaluation / "illustration_ground_truth.jsonl",
            candidate_count=illustration_test_count,
            query_count=len(illustration_queries),
            concept_count=len({row["concept_id"] for row in illustration_queries}),
            language_counts=illustration_languages,
        ),
    }


def sync_splits(meta_by_id: dict[str, dict[str, Any]]) -> None:
    for split_dir in SPLIT_DIRECTORIES.values():
        for path in split_dir.glob("*.jsonl"):
            rows = read_jsonl(path)
            out = []
            for old in rows:
                new = dict(meta_by_id[old["asset_id"]])
                # Keep split-local fields useful to consumers while making metadata canonical.
                new["dataset_split"] = old.get("dataset_split", path.stem)
                out.append(new)
            write_jsonl(path, out)


def _style_counts(meta: list[dict[str, Any]]) -> dict[str, int]:
    return {style: sum(row.get("visual_style") == style for row in meta) for style in SPLIT_DIRECTORIES}


def refresh_manifest(
    path: Path,
    meta: list[dict[str, Any]],
    *,
    source_metadata_path: str,
    split_path_prefix: str = "data/splits",
) -> dict[str, Any]:
    """Refresh manifest checksums against the exact files it declares as canonical."""
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.setdefault("source_metadata", {})["path"] = source_metadata_path
    manifest["source_metadata"]["sha256"] = hashlib.sha256(META.read_bytes()).hexdigest()
    manifest["source_metadata"]["asset_count"] = len(meta)
    manifest["style_counts"] = _style_counts(meta)
    manifest.setdefault("splits", {})

    for style, split_dir in SPLIT_DIRECTORIES.items():
        counts = split_counts(split_dir)
        style_entry = manifest["splits"].setdefault(style, {})
        style_entry["counts"] = counts
        style_entry["total"] = sum(counts.values())
        files_entry = style_entry.setdefault("files", {})
        for split_name, count in counts.items():
            checksum = hashlib.sha256((split_dir / f"{split_name}.jsonl").read_bytes()).hexdigest()
            style_entry.setdefault(split_name, {})["count"] = count
            style_entry[split_name]["sha256"] = checksum
            files_entry.setdefault(split_name, {})["count"] = count
            files_entry[split_name]["sha256"] = checksum
            if style == "pixel_art" and split_path_prefix == "data/splits":
                files_entry[split_name]["path"] = f"{split_path_prefix}/{split_name}.jsonl"
            else:
                split_folder = "pixel_art" if style == "pixel_art" else style
                files_entry[split_name]["path"] = f"{split_path_prefix}/{split_folder}/{split_name}.jsonl"
    write_json(path, manifest)
    return manifest


def sync_handoff(meta: list[dict[str, Any]]) -> None:
    handoff = ROOT / "handoff/backend_vector_db"
    if not handoff.exists():
        return

    shutil.copy2(META, handoff / "final_search_assets_pretty.json")
    evaluation = ROOT / "data/evaluation"
    for name in (
        "evaluation_queries.jsonl",
        "ground_truth.jsonl",
        "multimodal_queries.jsonl",
        "multimodal_ground_truth.jsonl",
        "illustration_evaluation_queries.jsonl",
        "illustration_ground_truth.jsonl",
        "evaluation_summary.json",
        "multimodal_evaluation_summary.json",
        "illustration_evaluation_summary.json",
    ):
        shutil.copy2(evaluation / name, handoff / "evaluation" / name)

    for style, source in SPLIT_DIRECTORIES.items():
        target = handoff / "splits" / style
        target.mkdir(parents=True, exist_ok=True)
        for name in ("train.jsonl", "validation.jsonl", "test.jsonl"):
            shutil.copy2(source / name, target / name)
        summary = refresh_split_summary(target / "split_summary.json", source, style)
        # A copied handoff package is self-contained, so point its summary at its local metadata file.
        summary["source_metadata"] = "../../final_search_assets_pretty.json"
        write_json(target / "split_summary.json", summary)

    refresh_manifest(
        handoff / "final_manifest.json",
        meta,
        source_metadata_path="final_search_assets_pretty.json",
        split_path_prefix="splits",
    )

    reports = ROOT / "reports"
    handoff_reports = handoff / "reports"
    handoff_reports.mkdir(parents=True, exist_ok=True)
    for name in (
        "FINAL_VALIDATION_REPORT_KO.md",
        "REDTEAM_DATA_AUDIT_KO.md",
        "RENDERED_ICON_SPLIT_POLICY_KO.md",
    ):
        source = reports / name
        if source.exists():
            shutil.copy2(source, handoff_reports / name)


def refresh_release_artifacts(meta: list[dict[str, Any]]) -> None:
    """Refresh every generated release artifact after canonical JSONL changes."""
    refresh_split_summaries()
    refresh_evaluation_summaries()
    refresh_manifest(
        ROOT / "data/metadata/final_manifest.json",
        meta,
        source_metadata_path="data/metadata/final_search_assets_pretty.json",
    )
    sync_handoff(meta)


def main() -> None:
    meta = json.loads(META.read_text(encoding="utf-8"))
    by_id = {row["asset_id"]: row for row in meta}
    # Remove a UTF-8 BOM from the canonical JSONL without changing its records.
    canonical = ROOT / "data/metadata/final_search_assets.jsonl"
    write_jsonl(canonical, read_jsonl(canonical))
    sync_splits(by_id)
    refresh_release_artifacts(meta)


if __name__ == "__main__":
    main()
