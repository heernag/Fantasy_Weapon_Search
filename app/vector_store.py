"""FAISS 인덱스와 벡터 순서에 대응하는 asset ID 목록을 함께 관리한다."""

import json
from pathlib import Path

import faiss
import numpy as np


class FaissVectorStore:
    """FAISS의 위치 인덱스를 외부 asset_id로 변환하는 얇은 저장소 계층."""
    def __init__(self, index_path: Path, ids_path: Path):
        self.index = faiss.read_index(str(index_path))
        self.asset_ids: list[str] = json.loads(ids_path.read_text(encoding="utf-8"))
        if self.index.ntotal != len(self.asset_ids):
            raise ValueError("FAISS 벡터 수와 asset ID 수가 일치하지 않습니다")
        self.position_by_id = {asset_id: position for position, asset_id in enumerate(self.asset_ids)}

    # ------------------------------------------------------------------
    # [미사용] 아래 두 메서드는 호출하는 곳이 없다.
    #
    # 실제 검색 랭킹은 src/retrieval/search_service_adapter.py의
    # `_rank_with_faiss`가 수행하고, 이 클래스는 scripts/build_final_index.py가
    # manifest를 만들 때 생성자와 `.index`/`.asset_ids`만 쓴다. 차원 불일치
    # 검증도 어댑터의 `_configure_faiss_index`와 `_rank_with_faiss`에 같은
    # 취지의 검사가 따로 있다.
    #
    # 저장소가 git으로 관리되지 않아 삭제하면 되살릴 수 없으므로 주석으로 남긴다.
    # 다시 쓰려면 아래 주석을 풀고 호출부를 추가하면 된다.
    # ------------------------------------------------------------------
#     def search(self, vector: np.ndarray, fetch_k: int) -> list[tuple[str, float]]:
#         """단일 질의 벡터를 검증하고 점수 내림차순 asset ID 목록을 반환한다."""
#         query = np.asarray(vector, dtype="float32")
#         if query.ndim != 2 or query.shape[0] != 1:
#             raise ValueError(f"검색 벡터 shape은 (1, {self.index.d})여야 합니다: {query.shape}")
#         if query.shape[1] != self.index.d:
#             # 1번 모델을 교체한 뒤 기존 인덱스를 그대로 쓰는 실수를 조기에 차단한다.
#             raise ValueError(
#                 f"검색 벡터 차원({query.shape[1]})과 FAISS 인덱스 차원({self.index.d})이 다릅니다. "
#                 "동일한 모델로 인덱스를 다시 생성하세요."
#             )
#         if not np.isfinite(query).all():
#             raise ValueError("검색 벡터에 NaN 또는 무한대가 포함되어 있습니다")
#
#         # FAISS 구현별 과도한 k 처리 차이를 피하기 위해 실제 벡터 수로 제한한다.
#         fetch_k = min(max(int(fetch_k), 0), len(self.asset_ids))
#         if fetch_k == 0:
#             return []
#         scores, positions = self.index.search(query, fetch_k)
#         return [
#             (self.asset_ids[position], float(score))
#             for position, score in zip(positions[0], scores[0])
#             if position >= 0
#         ]
#
#     def vector_for_asset_id(self, asset_id: str) -> np.ndarray:
#         position = self.position_by_id[asset_id]
#         return np.asarray(self.index.reconstruct(position), dtype="float32")
