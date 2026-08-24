import faiss
import numpy as np
import pytest

from src.retrieval.search_service_adapter import WeaponSearchService


class RecordingIndex:
    def __init__(self, vectors: np.ndarray):
        self.inner = faiss.IndexFlatIP(vectors.shape[1])
        self.inner.add(vectors.astype("float32"))
        self.d = self.inner.d
        self.ntotal = self.inner.ntotal
        self.search_calls: list[int] = []

    def search(self, query: np.ndarray, k: int):
        self.search_calls.append(k)
        return self.inner.search(query, k)

    def reconstruct(self, position: int):
        return self.inner.reconstruct(position)


def make_service(vectors: np.ndarray | None = None) -> WeaponSearchService:
    vectors = vectors if vectors is not None else np.eye(2, dtype="float32")
    service = WeaponSearchService.__new__(WeaponSearchService)
    service.image_embeddings = vectors
    service.asset_ids = [f"asset_{index}" for index in range(len(vectors))]
    service.metadata = {
        asset_id: {"asset_id": asset_id, "category": "keep", "processed_file": f"{asset_id}.png"}
        for asset_id in service.asset_ids
    }
    return service


def test_official_service_rejects_faiss_dimension_mismatch():
    service = make_service()
    wrong = RecordingIndex(np.eye(2, 3, dtype="float32"))

    with pytest.raises(ValueError, match="dimension"):
        service._configure_faiss_index(wrong, service.asset_ids)


def test_official_service_rejects_faiss_vector_count_mismatch():
    service = make_service()
    short = RecordingIndex(np.array([[1.0, 0.0]], dtype="float32"))

    with pytest.raises(ValueError, match="vector count"):
        service._configure_faiss_index(short, ["asset_0"])


def test_official_service_rejects_faiss_asset_order_mismatch():
    service = make_service()
    index = RecordingIndex(service.image_embeddings)

    with pytest.raises(ValueError, match="asset ID order"):
        service._configure_faiss_index(index, list(reversed(service.asset_ids)))


def test_official_service_configures_consistent_faiss_bundle():
    service = make_service()
    index = RecordingIndex(service.image_embeddings)

    service._configure_faiss_index(index, service.asset_ids)

    assert service.faiss_index is index
    assert service.faiss_asset_ids == service.asset_ids


def test_official_service_ranks_through_faiss_and_expands_for_filters():
    vectors = np.array(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.8, 0.2],
            [0.7, 0.3],
        ],
        dtype="float32",
    )
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    service = make_service(vectors)
    service.metadata["asset_0"]["category"] = "skip"
    service.metadata["asset_1"]["category"] = "skip"
    index = RecordingIndex(vectors)
    service._configure_faiss_index(index, service.asset_ids)

    results = service._rank_with_faiss(
        np.array([1.0, 0.0], dtype="float32"),
        candidate_indices=[2, 3],
        top_k=2,
    )

    assert [row[0] for row in results] == [2, 3]
    assert index.search_calls[0] == 2
    assert index.search_calls[-1] == 4


def test_official_scalar_filters_include_original_design_fields():
    record = {"style": "medieval", "handedness": "two_handed"}

    assert WeaponSearchService._matches_filters(
        record,
        {"style": "medieval", "handedness": "two_handed"},
    )
