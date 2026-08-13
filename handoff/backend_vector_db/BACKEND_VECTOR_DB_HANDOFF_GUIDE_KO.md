# 백엔드·Vector DB 작업 전달 보고서

상세 작업 절차는 저장소의 [BACKEND_VECTOR_DB_HANDOFF_GUIDE_KO.md](../../reports/BACKEND_VECTOR_DB_HANDOFF_GUIDE_KO.md)를 따른다.

핵심 기준:

- `final_manifest.json` 상태가 `final`인지 확인
- 총 1,391개, pixel_art 957 / illustration 284 / rendered_icon 150
- 스타일별 split을 독립적으로 임베딩
- `source_url`을 API의 `source`로 매핑
- 정답 ID는 각 `ground_truth.jsonl`에서 읽기
- Recall@K, MRR, mAP를 스타일·필터별로 측정
