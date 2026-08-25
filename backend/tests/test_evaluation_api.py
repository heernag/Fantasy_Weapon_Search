from app.main import EVALUATION_SUMMARY_FILES, evaluation_metrics, evaluation_summary, load_evaluation_metrics, load_evaluation_summaries


def test_evaluation_summary_uses_only_the_declared_files():
    payload = load_evaluation_summaries()

    assert set(payload) == set(EVALUATION_SUMMARY_FILES)
    assert payload["text_search"]["query_count"] == 160
    assert payload["multimodal_test"]["query_count"] == 80
    assert payload["multimodal_validation"]["dataset_split"] == "validation"
    assert payload["illustration_test"]["candidate_asset_count"] == 37


def test_evaluation_endpoint_returns_the_summary_payload():
    payload = evaluation_summary()

    assert payload["text_search"]["dataset_split"] == "test"
    assert payload["multimodal_test"]["ground_truth"]["relevance"] == "binary"


def test_evaluation_metrics_expose_only_measured_quality_values():
    payload = load_evaluation_metrics()

    assert payload["quality_sets"][0]["recall_at_10"] is not None
    assert payload["quality_sets"][0]["mrr"] is not None
    assert payload["quality_sets"][1]["ndcg"] is not None
    assert payload["zero_result_rate"] is not None
    assert isinstance(payload["failed_queries"], list)
    assert payload["trend"]
    assert evaluation_metrics() == payload


def test_evaluation_metrics_include_measured_search_mode_comparison():
    payload = load_evaluation_metrics()

    modes = {row["key"]: row for row in payload["mode_comparison"]}
    assert set(modes) == {"image", "text", "multimodal"}
    assert modes["image"]["image_weight"] == 1.0
    assert modes["text"]["text_weight"] == 1.0
    assert modes["multimodal"]["metrics"]["mrr"] is not None
