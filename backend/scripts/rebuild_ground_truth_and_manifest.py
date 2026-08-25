"""Rebuild evaluation ground truth and every release-derived artifact."""
from __future__ import annotations
import json
from pathlib import Path

from finalize_dataset import refresh_release_artifacts
from refresh_release_docs import refresh_release_docs

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

def main():
    meta=jl(ROOT/"data/metadata/final_search_assets.jsonl")
    pixel=jl(ROOT/"data/splits/test.jsonl"); ill=jl(ROOT/"data/splits/illustration/test.jsonl")
    rebuild_text(meta,pixel); rebuild_multimodal(meta,pixel); rebuild_illustration(ill)
    pretty_meta = json.loads((ROOT / "data/metadata/final_search_assets_pretty.json").read_text(encoding="utf-8"))
    refresh_release_artifacts(pretty_meta)
    refresh_release_docs()
    print("ground truth, release artifacts, and release docs rebuilt")

if __name__ == '__main__': main()
