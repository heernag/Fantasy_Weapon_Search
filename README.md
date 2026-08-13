# 판타지 무기 멀티모달 검색 데이터셋

픽셀아트와 일러스트 판타지 무기 이미지를 검색 모델·Vector DB·평가에 사용할 수 있도록 정리한 최종 데이터 패키지입니다.

## 핵심 파일

- `data/metadata/final_search_assets.jsonl`: 모델과 검색 시스템에서 읽는 통합 메타데이터
- `data/metadata/final_search_assets_pretty.json`: 사람이 검수하기 쉬운 통합 메타데이터
- `data/metadata/asset_sources.jsonl`: 에셋별 출처·저작자·라이선스 기록
- `data/metadata/tag_dictionary.json`: 실제 메타데이터 값으로 만든 태그 사전
- `data/processed/pixel_art/`: 픽셀아트 이미지
- `data/processed/rendered_icon/`: 렌더 아이콘 이미지
- `data/processed/illustration/`: 일러스트 이미지 284개
- `data/evaluation/`: 텍스트 검색 및 이미지+문장 결합검색 평가 자료
- `reports/`: 품질 검증과 데이터 분포 보고서

모든 `processed_file` 값은 이 저장소 루트를 기준으로 한 상대 경로입니다.

## 현재 데이터 개수

- 통합 메타데이터: 1,391개
- 픽셀아트: 957개
- 렌더 아이콘: 150개
- 일러스트: 284개

모든 처리 이미지는 RGB PNG, 224×224, 배경색 `#E8EBEF` 형식입니다.

## 일러스트 전용 분할

- `data/splits/illustration/train.jsonl`: 229개
- `data/splits/illustration/validation.jsonl`: 18개
- `data/splits/illustration/test.jsonl`: 37개
- `data/splits/illustration/split_summary.json`: 분할 개수와 카테고리 분포

같은 디자인의 색상·형태 변형은 하나의 그룹으로 묶어 서로 다른 split에 들어가지 않도록 했습니다.

## 출처와 라이선스

각 에셋은 출처·저작자·라이선스 정보를 기록했습니다.

- 출처 이름과 URL
- 저작자
- 라이선스 이름과 URL
- 원본 파일명
- 이미지 SHA-256

자세한 내용은 `reports/ILLUSTRATION_SOURCE_LICENSE_REPORT_KO.md`와 `data/metadata/asset_sources.jsonl`에서 확인할 수 있습니다.

## 검수 상태

이미지 유효성·중복·출처·라이선스와 메타데이터를 검수했습니다. 픽셀아트 957개는 `train 772 / validation 94 / test 91`, 일러스트 284개는 `229 / 18 / 37`, 렌더 아이콘 150개는 `121 / 15 / 14`로 분리되어 있습니다. 동일 perceptual-hash 변형은 한 split에만 배치했습니다.

최종 자동 검증 결과는 `reports/FINAL_VALIDATION_REPORT_KO.md`를 확인하세요.
