"""Create an in-split multimodal validation set for fusion-weight selection."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_PATH = ROOT / "data/splits/validation.jsonl"
EVALUATION_DIR = ROOT / "data/evaluation"
QUERY_PATH = EVALUATION_DIR / "multimodal_validation_queries.jsonl"
GROUND_TRUTH_PATH = EVALUATION_DIR / "multimodal_validation_ground_truth.jsonl"
SUMMARY_PATH = EVALUATION_DIR / "multimodal_validation_evaluation_summary.json"

TYPE_SPECS = {
    "color_change": ("primary_color", 16),
    "element_change": ("elements", 10),
    "material_change": ("materials", 10),
    "style_change": ("style_variant", 4),
}
SELECTION_ORDER = ("style_change", "element_change", "material_change", "color_change")
OUTPUT_ORDER = ("color_change", "element_change", "material_change", "style_change")

KO_TERMS = {
    "black": "검은색",
    "blue": "파란색",
    "bronze": "청동",
    "brown": "갈색",
    "cyan": "청록색",
    "gold": "금색",
    "gray": "회색",
    "green": "초록색",
    "orange": "주황색",
    "purple": "보라색",
    "red": "빨간색",
    "silver": "은색",
    "white": "흰색",
    "yellow": "노란색",
    "fire": "불",
    "holy": "신성",
    "ice": "얼음",
    "lightning": "번개",
    "poison": "독",
    "water": "물",
    "wind": "바람",
    "dark": "어둠",
    "bone": "뼈",
    "bronze": "청동",
    "cloth": "천",
    "crystal": "수정",
    "gold": "금",
    "leather": "가죽",
    "obsidian": "흑요석",
    "steel": "강철",
    "wood": "나무",
    "classic_pixel_art": "클래식 픽셀아트",
    "rendered_pixel_icon": "렌더 픽셀 아이콘",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def contains_value(row: dict[str, Any], field: str, value: str) -> bool:
    actual = row.get(field)
    return value in actual if isinstance(actual, list) else actual == value


def values_for_group(rows: list[dict[str, Any]], field: str) -> list[str]:
    values: set[str] = set()
    for row in rows:
        actual = row.get(field)
        if isinstance(actual, list):
            values.update(value for value in actual if isinstance(value, str) and value)
        elif isinstance(actual, str) and actual:
            values.add(actual)
    return sorted(values)


def build_candidates(rows: list[dict[str, Any]], query_type: str, field: str) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["category"], row["subcategory"])].append(row)

    candidates: list[dict[str, Any]] = []
    for (category, subcategory), group in sorted(groups.items()):
        if len(group) < 2:
            continue
        for source in sorted(group, key=lambda row: row["asset_id"]):
            for target_value in values_for_group(group, field):
                if contains_value(source, field, target_value):
                    continue
                relevant_ids = sorted(
                    row["asset_id"]
                    for row in group
                    if row["asset_id"] != source["asset_id"] and contains_value(row, field, target_value)
                )
                if relevant_ids:
                    candidates.append(
                        {
                            "query_type": query_type,
                            "field": field,
                            "source": source,
                            "target_value": target_value,
                            "relevant_ids": relevant_ids,
                            "preserve_filters": {"category": category, "subcategory": subcategory},
                            "target_filters": {field: target_value},
                        }
                    )
    return sorted(
        candidates,
        key=lambda item: (
            len(item["relevant_ids"]),
            item["preserve_filters"]["category"],
            item["preserve_filters"]["subcategory"],
            item["source"]["asset_id"],
            item["target_value"],
        ),
    )


def select_candidates(
    candidates: list[dict[str, Any]], count: int, source_usage: Counter[str]
) -> list[dict[str, Any]]:
    """Choose a balanced deterministic subset while avoiding source-image overuse."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        buckets[candidate["preserve_filters"]["category"]].append(candidate)

    selected: list[dict[str, Any]] = []
    positions = {category: 0 for category in sorted(buckets)}
    seen: set[tuple[str, str, str]] = set()
    while len(selected) < count:
        progress = False
        for category in sorted(buckets):
            bucket = buckets[category]
            while positions[category] < len(bucket):
                candidate = bucket[positions[category]]
                positions[category] += 1
                source_id = candidate["source"]["asset_id"]
                signature = (source_id, candidate["field"], candidate["target_value"])
                if source_usage[source_id] >= 2 or signature in seen:
                    continue
                selected.append(candidate)
                source_usage[source_id] += 1
                seen.add(signature)
                progress = True
                break
            if len(selected) == count:
                break
        if not progress:
            raise RuntimeError(f"Could not select {count} validation concepts; selected {len(selected)}")
    return selected


def build_concepts(rows: list[dict[str, Any]], max_concepts_per_type: int | None = None) -> list[dict[str, Any]]:
    """Build deterministic concepts whose references and answers are all in validation."""
    source_usage: Counter[str] = Counter()
    selected_by_type: dict[str, list[dict[str, Any]]] = {}
    for query_type in SELECTION_ORDER:
        field, default_count = TYPE_SPECS[query_type]
        count = max_concepts_per_type if max_concepts_per_type is not None else default_count
        selected_by_type[query_type] = select_candidates(build_candidates(rows, query_type, field), count, source_usage)
    return [concept for query_type in OUTPUT_ORDER for concept in selected_by_type[query_type]]


def modification_text(query_type: str, value: str, language: str) -> str:
    korean = KO_TERMS.get(value, value.replace("_", " "))
    english = value.replace("_", " ")
    if language == "ko":
        templates = {
            "color_change": f"{korean} 계열로 바꿔줘",
            "element_change": f"{korean} 속성이 있는 것으로 바꿔줘",
            "material_change": f"{korean} 재질이 들어간 것으로 바꿔줘",
            "style_change": f"{korean} 스타일로 바꿔줘",
        }
    else:
        templates = {
            "color_change": f"change it to a {english} color scheme",
            "element_change": f"change it to one with {english} elemental traits",
            "material_change": f"change it to one made with {english}",
            "style_change": f"change it to the {english} style",
        }
    return templates[query_type]


def main() -> None:
    rows = read_jsonl(VALIDATION_PATH)
    if len(rows) != 94:
        raise RuntimeError(f"Expected 94 pixel-art validation assets, found {len(rows)}")
    if any(row.get("visual_style") != "pixel_art" for row in rows):
        raise RuntimeError("Validation split contains a non-pixel-art asset")

    concepts = build_concepts(rows)
    if len(concepts) != 40:
        raise RuntimeError(f"Expected 40 concepts, found {len(concepts)}")

    validation_ids = {row["asset_id"] for row in rows}
    queries: list[dict[str, Any]] = []
    truths: list[dict[str, Any]] = []
    for number, concept in enumerate(concepts, start=1):
        concept_id = f"mm_val_concept_{number:03d}"
        source = concept["source"]
        if source["asset_id"] not in validation_ids or not set(concept["relevant_ids"]) <= validation_ids:
            raise RuntimeError("A validation concept references an asset outside validation")
        for language in ("ko", "en"):
            query_id = f"mm_val_{language}_{number:03d}"
            queries.append(
                {
                    "query_id": query_id,
                    "concept_id": concept_id,
                    "language": language,
                    "query_type": concept["query_type"],
                    "query_image_id": source["asset_id"],
                    "query_image": source["processed_file"],
                    "modification_text": modification_text(concept["query_type"], concept["target_value"], language),
                    "preserve_filters": concept["preserve_filters"],
                    "target_filters": concept["target_filters"],
                    "excluded_asset_ids": [source["asset_id"]],
                    "candidate_split": "validation",
                }
            )
            truths.append(
                {
                    "query_id": query_id,
                    "concept_id": concept_id,
                    "query_image_id": source["asset_id"],
                    "relevant_asset_ids": concept["relevant_ids"],
                    "relevance": "binary",
                    "candidate_split": "validation",
                }
            )

    type_counts = Counter(concept["query_type"] for concept in concepts)
    relevant_counts = [len(concept["relevant_ids"]) for concept in concepts]
    summary = {
        "created_on": date.today().isoformat(),
        "dataset_split": "validation",
        "candidate_asset_count": len(rows),
        "concept_count": len(concepts),
        "query_count": len(queries),
        "language_counts": {"ko": 40, "en": 40},
        "query_type_concept_counts": dict(type_counts),
        "category_concept_counts": dict(sorted(Counter(c["preserve_filters"]["category"] for c in concepts).items())),
        "source_image_count": len({concept["source"]["asset_id"] for concept in concepts}),
        "maximum_concepts_per_source_image": max(Counter(c["source"]["asset_id"] for c in concepts).values()),
        "ground_truth": {
            "relevance": "binary",
            "minimum_relevant_assets": min(relevant_counts),
            "maximum_relevant_assets": max(relevant_counts),
            "average_relevant_assets": round(sum(relevant_counts) / len(relevant_counts), 3),
        },
    }
    write_jsonl(QUERY_PATH, queries)
    write_jsonl(GROUND_TRUTH_PATH, truths)
    write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
