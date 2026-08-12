# 렌더 아이콘 데이터셋 split 정책

## 목적

렌더 아이콘은 픽셀아트와 시각적 특성이 다르므로 픽셀아트 split에 섞지 않고, `rendered_icon` 전용 데이터셋으로 독립 관리한다. 일러스트 split과도 분리해 검색·평가 시 스타일별 결과를 구분한다.

## 적용 기준

- 기준 메타데이터: `data/metadata/final_search_assets_pretty.json`
- 대상 조건: `visual_style == "rendered_icon"`
- 대상 수: 150개
- 고정 시드: `20260812`
- 분할 비율: train 80%, validation 10%, test 10%
- 실제 수량: train 120개, validation 15개, test 15개
- 분할 단위: `asset_id` 기준, 세 split 간 중복 금지

## 파일

- `data/splits/rendered_icon/train.jsonl`
- `data/splits/rendered_icon/validation.jsonl`
- `data/splits/rendered_icon/test.jsonl`
- `data/splits/rendered_icon/split_summary.json`

각 JSONL 행은 최종 메타데이터의 전체 행을 유지한다. 백엔드에서는 이 split을 픽셀아트·일러스트 split과 별도 인덱스로 취급하거나, 스타일 필터와 함께 통합 인덱스에 넣어야 한다.

## 검증 기준

1. 세 파일의 JSONL 파싱 성공
2. train/validation/test ID 교집합 0개
3. 세 split의 합집합 150개
4. 모든 ID가 최종 메타데이터와 렌더 아이콘 이미지에 존재
5. `visual_style`이 모든 행에서 `rendered_icon`
