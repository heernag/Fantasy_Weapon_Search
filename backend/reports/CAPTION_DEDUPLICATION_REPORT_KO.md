# 반복 캡션 정리 보고서

## 작업 결과

- 같은 영문·한글 캡션이 반복되면서 색상·재질·속성이 서로 다른 항목을 찾아 구분 정보를 캡션에 추가했습니다.
- 총 121개 에셋의 캡션을 보완했습니다.
- 동일한 태그 정보를 가진 변형 에셋은 불필요하게 문장을 늘리지 않고 같은 캡션을 유지했습니다.

## 반영 파일

- `data/metadata/final_search_assets_pretty.json`
- `data/metadata/final_search_assets.jsonl`
- `data/metadata/illustration_metadata.json`
- `data/metadata/illustration_assets.jsonl`
- `data/metadata/rendered_icon_assets.jsonl`
- `data/splits/train.jsonl`
- `data/splits/validation.jsonl`
- `data/splits/test.jsonl`

## 검증 결과

- 모든 분할 파일의 캡션이 기준 메타데이터와 일치합니다.
- `illustration_metadata.json`도 기준 메타데이터와 일치합니다.
- 작업 후에도 동일한 정보의 변형끼리 공유하는 반복 캡션은 남아 있습니다. 이는 오류가 아니라 동일한 검색 태그를 가진 색상 변형을 같은 문장으로 묶은 경우입니다.
- 현재 중복 그룹은 영문 56개, 한글 57개이며, 최대 반복 횟수는 각각 24회·25회입니다.

## 다음 권장 작업

CLIP 파인튜닝에서 에셋별 문장을 완전히 다르게 해야 한다면, 동일 태그 변형에도 `주요 색상` 또는 `asset_id` 기반의 짧은 식별 문구를 추가할 수 있습니다. 검색용 데이터로는 현재 상태도 사용할 수 있습니다.
