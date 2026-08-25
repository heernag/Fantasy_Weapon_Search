"""Keep exact perceptual-hash variants in one split and rebuild split rows."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]

def dump(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8", newline="\n")

def regroup(style):
    meta = [row for row in jl(ROOT / "data/metadata/final_search_assets.jsonl") if row.get("visual_group") == style]
    by_id = {row["asset_id"]: row for row in meta}
    current = {}
    rows = {split: jl(ROOT / f"data/splits/{style}/{split}.jsonl") for split in ("train", "validation", "test")}
    for split, items in rows.items():
        for item in items:
            current[item["asset_id"]] = split
    groups = defaultdict(list)
    for row in meta:
        groups[row.get("perceptual_hash", row["asset_id"])].append(row["asset_id"])
    priority = {"train": 0, "validation": 1, "test": 2}
    target = dict(current)
    for ids in groups.values():
        if len(ids) < 2:
            continue
        counts = Counter(current[item] for item in ids)
        owner = sorted(counts, key=lambda split: (-counts[split], priority[split]))[0]
        for item in ids:
            target[item] = owner
    if style == "illustration":
        # Keep every illustration evaluation filter represented in test.
        queries = jl(ROOT / "data/evaluation/illustration_evaluation_queries.jsonl")
        def match(row, filters):
            for key, expected in filters.items():
                actual = row.get(key)
                values = expected if isinstance(expected, list) else [expected]
                if isinstance(actual, list):
                    if not all(value in actual for value in values): return False
                elif actual not in values: return False
            return True
        for query in queries:
            filters = query.get("expected_filters", {})
            if any(match(by_id[item], filters) and target[item] == "test" for item in target):
                continue
            candidates = [item for item in target if match(by_id[item], filters)]
            if candidates:
                chosen = candidates[0]
                group = groups[by_id[chosen].get("perceptual_hash", chosen)]
                for item in group: target[item] = "test"
    out = {split: [] for split in rows}
    for asset_id, split in target.items():
        out[split].append(by_id[asset_id])
    for split in out:
        out[split].sort(key=lambda row: row["asset_id"])
        dump(ROOT / f"data/splits/{style}/{split}.jsonl", out[split])
    return {split: len(items) for split, items in out.items()}

if __name__ == "__main__":
    print("illustration", regroup("illustration"))
    print("rendered_icon", regroup("rendered_icon"))
