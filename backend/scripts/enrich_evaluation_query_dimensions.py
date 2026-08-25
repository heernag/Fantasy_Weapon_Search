"""Add stable, flattened comparison dimensions to evaluation query JSONL files."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "data/evaluation/multimodal_queries.jsonl", ROOT / "data/evaluation/multimodal_validation_queries.jsonl", ROOT / "data/evaluation/evaluation_queries.jsonl", ROOT / "data/evaluation/illustration_evaluation_queries.jsonl"]


def enrich(row: dict) -> dict:
    preserve, target = row.get("preserve_filters", {}), row.get("target_filters", {})
    mapping = {
        "weapon_category": preserve.get("category") or target.get("category"),
        "weapon_subcategory": preserve.get("subcategory") or target.get("subcategory"),
        "target_primary_color": target.get("primary_color"),
        "target_colors": target.get("colors", []),
        "target_elements": target.get("elements", []),
        "target_materials": target.get("materials", []),
        "target_shape_tags": target.get("shape_tags", []),
        "visual_style": preserve.get("visual_style") or target.get("visual_style"),
        "grade": target.get("grade"),
    }
    for key, value in mapping.items():
        if value is not None:
            row[key] = value
    return row


def main() -> None:
    for path in FILES:
        rows = [enrich(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
        print(f"enriched {len(rows)} queries: {path.name}")


if __name__ == "__main__":
    main()
