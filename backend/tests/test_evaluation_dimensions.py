import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_validation_queries_have_comparison_dimensions():
    rows = [json.loads(line) for line in (ROOT / "data/evaluation/multimodal_validation_queries.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert all("weapon_category" in row for row in rows)
    assert all("target_colors" in row and isinstance(row["target_colors"], list) for row in rows)
    assert any(row.get("target_primary_color") for row in rows)
