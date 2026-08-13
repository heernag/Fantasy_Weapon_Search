# 에셋 등급 적용 및 데이터 부실 항목 점검 보고서

작성일: 2026-08-11

## 1. 등급 적용 결과

전체 1,396개 에셋에 등급 필드를 추가했습니다.

| 등급 | 조건 | 수량 |
|---|---|---:|
| 일반등급 (`common`) | `elements`가 없거나 빈 목록 | 1,117 |
| 전설등급 (`legendary`) | `elements`에 하나 이상의 속성이 있음 | 279 |

각 레코드에 다음 두 필드를 함께 기록했습니다.

- `grade`: `common` 또는 `legendary`
- `grade_label_ko`: `일반등급` 또는 `전설등급`

픽셀아트, 일러스트, 렌더 아이콘 모두 동일한 기준을 적용했습니다.

## 2. 현재 데이터에서 확인된 부실·주의 항목

### 완료된 항목

- 캡션, 카테고리, 세부분류, 재질, 색상, 출처, 라이선스의 공백 레코드: 없음
- 전체 레코드 검수 상태: `confirmed`
- 출처·라이선스: CC0 1,246개, CC-BY 3.0 150개
- 등급 필드: 1,396개 전부 입력
- 픽셀아트 RGB 변환: 완료
- 픽셀아트 split: 962개(776/94/92)로 최신화

### 추가 확인이 필요한 부분

- 재질을 `unknown`으로 둔 에셋이 134개 있습니다. 이미지에서 재질을 확정하기 어려운 경우라서 남겨 둔 값입니다.
- `asset_001561`~`asset_001571` 11개는 `low_style_confidence` 경고가 있습니다. 지팡이류이므로 필요하면 스타일만 재검수할 수 있습니다.
- 출처의 `mapping_status`가 `ambiguous_archive`인 레코드가 161개 있습니다. 출처 URL과 라이선스는 기록되어 있지만, 원본 아카이브 파일과의 일대일 매칭은 불확실합니다.
- 동일한 캡션을 공유하는 그룹이 68개 남아 있습니다. 최대 24개 에셋이 같은 영문·한글 캡션을 공유하므로 CLIP 파인튜닝 전 추가 문장 다양화가 권장됩니다.
- 결합검색 평가는 80개가 마련되어 있습니다. 기존 텍스트 평가 160개와 합쳐 총 240개 질의지만, 결합검색만 160개로 확장된 상태는 아닙니다.

## 3. 반영 파일

- `data/metadata/final_search_assets_pretty.json`
- `data/metadata/final_search_assets.jsonl`
- `data/metadata/illustration_metadata.json`
- `data/metadata/illustration_assets.jsonl`
- `data/metadata/rendered_icon_assets.jsonl`
- `data/splits/train.jsonl`
- `data/splits/validation.jsonl`
- `data/splits/test.jsonl`
- `data/splits/split_manifest.jsonl`
- `data/metadata/tag_dictionary.json`

등급 적용 재실행 스크립트: `scripts/apply_asset_grades.py`
