# 최종 데이터 검증 보고서

- 갱신일: 2026-08-13
- 기준 메타데이터: `data/metadata/final_search_assets_pretty.json`
- 최종 에셋 수: **1,391개**

## 데이터 구성

| 스타일 | 에셋 수 | train | validation | test |
| --- | ---: | ---: | ---: | ---: |
| pixel_art | 957 | 772 | 94 | 91 |
| illustration | 284 | 229 | 18 | 37 |
| rendered_icon | 150 | 121 | 15 | 14 |
| 합계 | 1391 | 1122 | 127 | 142 |

## 검증 결과

- 메타데이터와 이미지 연결: 통과
- 에셋 ID 중복, split 간 ID 중복, JSONL BOM: 모두 0건
- 유사 변형 교차 split 누수: 일러스트 0그룹, 렌더 아이콘 0그룹
- 태그·색상·재질·속성·등급·한글/영문 캡션 누락: 0건
- 출처 및 라이선스 누락: 0건
- 정답 세트: 텍스트 160개, 이미지+문장 80개, 일러스트 100개 질의

## 전달 기준

백엔드에는 `handoff/backend_vector_db/`를 전달합니다. 그 폴더의 `final_manifest.json`은 같은 폴더의 `final_search_assets_pretty.json`과 `splits/` 경로를 기준으로 검증합니다.
