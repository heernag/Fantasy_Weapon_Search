# 판타지 무기 멀티모달 검색용 최종 데이터 패키지

이 폴더에는 검수가 끝난 픽셀아트 판타지 무기 에셋 1,113개와 검색·학습·평가에 필요한 최종 자료만 정리되어 있습니다.

## 바로 사용할 파일

- `data/metadata/final_search_assets.jsonl`: 모델 학습과 검색 인덱스 구축용 통합 메타데이터
- `data/metadata/final_search_assets_pretty.json`: 사람이 읽기 편한 통합 메타데이터
- `data/metadata/asset_sources.jsonl`: 에셋별 출처와 라이선스 기록
- `data/processed/pixel_art/`: 정규화된 최종 이미지 1,113개
- `data/splits/train.jsonl`: 모델 학습용 데이터 886개
- `data/splits/validation.jsonl`: 설정 선택과 성능 확인용 데이터 115개
- `data/splits/test.jsonl`: 최종 평가용 데이터 112개
- `data/evaluation/`: 한국어·영어 검색 평가 질의와 정답 세트
- `reports/`: 무결성 검증과 데이터 분포 분석 결과
- `docs/DATASET_GUIDE_KO.md`: 데이터 사용 안내서

모든 메타데이터의 `processed_file`은 이 폴더를 기준으로 한 상대 경로입니다. 예를 들어 `data/processed/pixel_art/asset_000057.png`처럼 사용하면 됩니다.

## 검색 평가 세트

`data/evaluation` 폴더에는 test 데이터 112개만 후보로 사용하는 평가 자료가 들어 있습니다.

- `evaluation_queries.jsonl`: 한국어 80개와 영어 80개, 총 160개 검색 질의
- `ground_truth.jsonl`: 각 질의에 해당하는 정답 에셋 ID
- `evaluation_results_template.json`: 검색 결과 지표 기록 양식
- `evaluation_summary.json`: 평가 세트 구성 요약
- `EVALUATION_GUIDE_KO.md`: 쉬운 사용 방법과 지표 설명

한국어와 영어 질의는 같은 검색 개념끼리 동일한 정답을 사용합니다. 자세한 실행 순서는 `data/evaluation/EVALUATION_GUIDE_KO.md`를 확인하세요.

## 최종 상태

- 전체 에셋: 1,113개
- train: 886개
- validation: 115개
- test: 112개
- `iron` 재질: 0개 (`steel`로 통일)
- 중복 ID: 0개
- 유사 이미지 그룹의 데이터 분할 누수: 0개
- 라이선스 확인 완료: 1,113개

기존 프로젝트의 검수용 파일, 임시 자료, 캐시, 작업 스크립트와 과거 백업은 이 최종 패키지에 포함하지 않았습니다.
