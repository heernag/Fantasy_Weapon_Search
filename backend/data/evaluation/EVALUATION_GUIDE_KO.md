# 텍스트 검색 평가 안내서

픽셀아트 test split의 91개 후보 이미지에서, 검색 문장에 맞는 이미지를 찾는 성능을 평가합니다.

## 구성

- 질의: 한글 80개, 영어 80개, 총 160개
- 정답: `ground_truth.jsonl`의 질의별 `relevant_asset_ids`
- 정답 수: 최소 1개 / 최대 65개 / 평균 6.938개
- 조건: 무기 종류, 세부 종류, 색상, 속성, 재질, 스타일, 손사용 태그

## 사용 규칙

1. 후보는 `data/splits/test.jsonl`에 있는 91개 픽셀아트 에셋만 사용합니다.
2. `evaluation_queries.jsonl`의 `query_id`와 `ground_truth.jsonl`의 같은 `query_id`를 연결합니다.
3. Recall@K, MRR, mAP는 이 정답 목록을 기준으로 계산합니다.
