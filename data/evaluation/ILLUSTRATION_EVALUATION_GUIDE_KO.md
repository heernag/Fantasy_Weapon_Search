# 일러스트 평가 세트 안내

일러스트 `test` split 27개를 검색 후보로 사용해 만든 전용 평가 세트입니다.

## 파일

- `illustration_evaluation_queries.jsonl`: 한글·영문 검색 질의 74개
- `illustration_ground_truth.jsonl`: 질의별 정답 에셋 ID
- `illustration_evaluation_summary.json`: 평가 세트 요약

## 구성

- 기준 split: `data/splits/illustration/test.jsonl`
- 질의 언어: 한글 37개, 영문 37개
- 질의 기준: category, subcategory, primary_color, elements, materials, handedness
- 정답 기준: 현재 일러스트 메타데이터의 필터와 일치하는 test 에셋

## 사용 방법

검색 모델에 `illustration_evaluation_queries.jsonl`의 `query_text`를 입력하고, 반환된 에셋 순위를 `illustration_ground_truth.jsonl`의 `relevant_asset_ids`와 비교합니다. Recall@K, MRR, mAP를 계산할 때는 반드시 일러스트 test 후보 27개만 사용합니다.

현재 세트는 텍스트 검색 평가용이며, 일러스트 기준 이미지+수정 문장 방식의 멀티모달 평가는 별도로 추가할 수 있습니다.
