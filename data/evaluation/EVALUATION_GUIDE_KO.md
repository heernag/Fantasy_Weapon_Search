# 판타지 무기 이미지 검색 평가 안내서

## 무엇을 평가하나요?

검색 문장을 입력했을 때 알맞은 무기 이미지를 얼마나 잘 찾는지 확인하는 정답 세트입니다. 검색 후보는 `test.jsonl`의 92개 에셋만 사용합니다.

## 평가 세트 구성

- 검색 개념: 80개
- 한국어 질의: 80개
- 영어 질의: 80개
- 전체 질의: 160개
- 기존 무기 종류·색상·속성·재질 질의에 `style`과 `handedness` 질의를 추가했습니다.

## 파일 설명

- `evaluation_queries.jsonl`: 검색 시스템에 입력할 한국어·영어 질의
- `ground_truth.jsonl`: 각 질의에 해당하는 정답 에셋 ID
- `evaluation_results_template.json`: 검색 성능 측정 결과 기록 양식
- `evaluation_summary.json`: 평가 세트 구성 요약

## 사용 순서

1. `evaluation_queries.jsonl`의 `query_text`를 검색 시스템에 입력합니다.
2. 검색 후보는 반드시 `data/splits/test.jsonl`의 에셋만 사용합니다.
3. 검색 결과의 에셋 ID를 순서대로 저장합니다.
4. `ground_truth.jsonl`의 `relevant_asset_ids`와 비교해 지표를 계산합니다.
5. 결과를 `evaluation_results_template.json` 형식으로 기록합니다.

## 권장 평가 지표

- `Recall@1`, `Recall@5`, `Recall@10`: 정답을 상위 K개 안에서 찾은 비율
- `Precision@5`, `Precision@10`: 상위 K개 결과 중 정답의 비율
- `MRR`: 첫 번째 정답이 얼마나 앞에 나오는지 측정
- `mAP`: 여러 정답의 검색 순위를 종합해 측정
- `nDCG@10`: 상위 10개 결과의 순서 품질 측정

## 주의사항

- 한국어와 영어 질의는 같은 `concept_id`를 공유하며 정답도 같습니다.
- `expected_filters`는 정답을 만든 메타데이터 조건입니다.
- 조건이 여러 개면 모든 조건을 만족해야 하는 AND 방식입니다.
- 평가 세트는 학습에 사용하지 말고 최종 성능 확인에만 사용합니다.
