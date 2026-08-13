"""Rebuild ground truth from current metadata and refresh manifests."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data/evaluation"
QUERY_REPAIRS = {
    "concept_054": {"category":"sword", "subcategory":"longsword", "primary_color":"blue", "elements":"ice", "materials":"wood"},
    "concept_056": {"category":"arrow", "subcategory":"poison_arrow", "primary_color":"green", "elements":"poison", "materials":["wood","steel"]},
}

def jl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

def dump(path, rows):
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8", newline="\n")

def matches(row, filters):
    for field, expected in filters.items():
        actual = row.get(field)
        expected_values = expected if isinstance(expected, list) else [expected]
        if isinstance(actual, list):
            if not all(v in actual for v in expected_values): return False
        elif actual not in expected_values: return False
    return True

def rebuild_text(meta, split):
    qs = jl(EVAL / "evaluation_queries.jsonl")
    gt=[]
    for q in qs:
        if q.get("concept_id") in QUERY_REPAIRS:
            q["expected_filters"] = QUERY_REPAIRS[q["concept_id"]]
        ids=sorted(r["asset_id"] for r in split if matches(r,q.get("expected_filters",{})))
        if not ids: raise ValueError(f"No text ground truth for {q['query_id']}")
        gt.append({"query_id":q["query_id"],"concept_id":q["concept_id"],"relevant_asset_ids":ids,"relevance":"binary","candidate_split":"test"})
    dump(EVAL/"ground_truth.jsonl",gt)
    dump(EVAL/"evaluation_queries.jsonl", qs)

def rebuild_multimodal(meta, split):
    qs=jl(EVAL/"multimodal_queries.jsonl"); gt=[]
    for q in qs:
        filters={**q.get("preserve_filters",{}),**q.get("target_filters",{})}
        ids=sorted(r["asset_id"] for r in split if r["asset_id"] not in q.get("excluded_asset_ids",[]) and matches(r,filters))
        if not ids: raise ValueError(f"No multimodal ground truth for {q['query_id']}")
        gt.append({"query_id":q["query_id"],"concept_id":q["concept_id"],"query_image_id":q["query_image_id"],"relevant_asset_ids":ids,"relevance":"binary","candidate_split":"test"})
    dump(EVAL/"multimodal_ground_truth.jsonl",gt)

def rebuild_illustration(split):
    qs=jl(EVAL/"illustration_evaluation_queries.jsonl"); gt=[]
    for q in qs:
        ids=sorted(r["asset_id"] for r in split if matches(r,q.get("expected_filters",{})))
        if not ids: raise ValueError(f"No illustration ground truth for {q['query_id']}")
        gt.append({"query_id":q["query_id"],"concept_id":q["concept_id"],"candidate_split":"test","relevance":"binary","relevant_asset_ids":ids})
    dump(EVAL/"illustration_ground_truth.jsonl",gt)

def refresh_manifest(path, meta, split_counts):
    if not path.exists(): return
    d=json.loads(path.read_text(encoding="utf-8"))
    d.setdefault("source_metadata",{})["sha256"] = hashlib.sha256((ROOT/"data/metadata/final_search_assets_pretty.json").read_bytes()).hexdigest()
    d["source_metadata"]["asset_count"] = len(meta)
    d["style_counts"] = {"pixel_art":957,"illustration":284,"rendered_icon":150}
    d.setdefault("splits",{})
    for name, counts in split_counts.items():
        d["splits"].setdefault(name,{})["counts"] = counts
        d["splits"][name]["total"] = sum(counts.values())
        for split, count in counts.items():
            candidates = [
                ROOT / "data/splits" / name / f"{split}.jsonl",
                ROOT / "data/splits" / f"{split}.jsonl" if name == "pixel_art" else ROOT / "data/splits" / name / f"{split}.jsonl",
            ]
            src = next((candidate for candidate in candidates if candidate.exists()), None)
            if src is None:
                continue
            entry = d["splits"][name].setdefault(split, {})
            entry["count"] = count
            entry["sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
            files = d["splits"][name].setdefault("files", {})
            file_entry = files.setdefault(split, {})
            file_entry["count"] = count
            file_entry["sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")

def main():
    meta=jl(ROOT/"data/metadata/final_search_assets.jsonl")
    pixel=jl(ROOT/"data/splits/test.jsonl"); ill=jl(ROOT/"data/splits/illustration/test.jsonl")
    rebuild_text(meta,pixel); rebuild_multimodal(meta,pixel); rebuild_illustration(ill)
    counts={}
    for name, directory in (("pixel_art", ROOT / "data/splits"), ("illustration", ROOT / "data/splits/illustration"), ("rendered_icon", ROOT / "data/splits/rendered_icon")):
        counts[name] = {split: len(jl(directory / f"{split}.jsonl")) for split in ("train", "validation", "test")}
    refresh_manifest(ROOT/"data/metadata/final_manifest.json",meta,counts)
    refresh_manifest(ROOT/"handoff/backend_vector_db/final_manifest.json",meta,counts)
    print('ground truth rebuilt')

if __name__ == '__main__': main()
