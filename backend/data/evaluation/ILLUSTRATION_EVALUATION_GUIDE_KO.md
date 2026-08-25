# 일러스트 평가 세트 안내

일러스트 `test` split 37개를 검색 후보로 사용하는 전용 텍스트 검색 평가 세트입니다.

## 구성

- 질의: 한글 50개, 영어 50개, 총 질의 100개
- 정답 수: 최소 1개 / 최대 36개 / 평균 5.840개
- 질의 조건: category, subcategory, primary_color, elements, materials, handedness

`illustration_evaluation_queries.jsonl`의 `query_id`와 `illustration_ground_truth.jsonl`의 동일 `query_id`를 연결해 Recall@K, MRR, mAP를 계산합니다. 후보에는 일러스트 test split 37개만 포함해야 합니다.
