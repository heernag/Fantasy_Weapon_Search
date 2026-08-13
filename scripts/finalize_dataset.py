"""Synchronize final metadata, split records, evaluation summaries, and docs."""
from __future__ import annotations

import json
import shutil
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/metadata/final_search_assets_pretty.json"


def read_jsonl(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def sync_splits(meta_by_id):
    for path in list((ROOT / "data/splits").glob("*.jsonl")) + list((ROOT / "data/splits/illustration").glob("*.jsonl")) + list((ROOT / "data/splits/rendered_icon").glob("*.jsonl")):
        rows = read_jsonl(path)
        out = []
        for old in rows:
            new = dict(meta_by_id[old["asset_id"]])
            # Keep split-local fields useful to consumers while making metadata canonical.
            new["dataset_split"] = old.get("dataset_split", path.stem)
            out.append(new)
        write_jsonl(path, out)


def update_summary(path: Path, candidate_count: int, query_count: int, concept_count: int | None = None):
    data = json.loads(path.read_text(encoding="utf-8"))
    data["candidate_asset_count"] = candidate_count
    data["query_count"] = query_count
    if concept_count is not None:
        data["concept_count"] = concept_count
        query_rows = read_jsonl(ROOT / "data/evaluation/illustration_evaluation_queries.jsonl")
        data["language_counts"] = {"ko": sum(r.get("language") == "ko" for r in query_rows), "en": sum(r.get("language") == "en" for r in query_rows)}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    by_id = {row["asset_id"]: row for row in meta}
    # Remove the UTF-8 BOM from the canonical JSONL without changing its records.
    canonical = ROOT / "data/metadata/final_search_assets.jsonl"
    rows = read_jsonl(canonical)
    write_jsonl(canonical, rows)
    sync_splits(by_id)

    pixel_test = len(read_jsonl(ROOT / "data/splits/test.jsonl"))
    update_summary(ROOT / "data/evaluation/evaluation_summary.json", pixel_test, 160)
    update_summary(ROOT / "data/evaluation/multimodal_evaluation_summary.json", pixel_test, 80)
    illustration_test = len(read_jsonl(ROOT / "data/splits/illustration/test.jsonl"))
    illustration_queries = read_jsonl(ROOT / "data/evaluation/illustration_evaluation_queries.jsonl")
    concepts = len({row["concept_id"] for row in illustration_queries})
    update_summary(ROOT / "data/evaluation/illustration_evaluation_summary.json", illustration_test, len(illustration_queries), concepts)

    # Refresh the backend handoff package from the same canonical files.
    handoff = ROOT / "handoff/backend_vector_db"
    if handoff.exists():
        shutil.copy2(META, handoff / "final_search_assets_pretty.json")
        for name in ("evaluation_queries.jsonl", "ground_truth.jsonl", "multimodal_queries.jsonl", "multimodal_ground_truth.jsonl", "illustration_evaluation_queries.jsonl", "illustration_ground_truth.jsonl"):
            shutil.copy2(ROOT / "data/evaluation" / name, handoff / "evaluation" / name)
        for dataset, source in (("pixel_art", ROOT / "data/splits"), ("illustration", ROOT / "data/splits/illustration"), ("rendered_icon", ROOT / "data/splits/rendered_icon")):
            target = handoff / "splits" / dataset
            target.mkdir(parents=True, exist_ok=True)
            for name in ("train.jsonl", "validation.jsonl", "test.jsonl", "split_summary.json"):
                if (source / name).exists(): shutil.copy2(source / name, target / name)
        manifest_path = handoff / "final_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_metadata"]["sha256"] = hashlib.sha256(META.read_bytes()).hexdigest()
            manifest["source_metadata"]["asset_count"] = len(meta)
            manifest["style_counts"] = {
                "pixel_art": len([r for r in meta if r.get("visual_style") == "pixel_art"]),
                "illustration": len([r for r in meta if r.get("visual_style") == "illustration"]),
                "rendered_icon": len([r for r in meta if r.get("visual_style") == "rendered_icon"]),
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
