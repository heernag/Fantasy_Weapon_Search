# 픽셀아트 스타일 세부 분류 감사 보고서

## 검사 대상

- 전체 에셋: 1,113개
- 재분류 전 `visual_style`: 1,113개 모두 `pixel_art`
- 현재 `visual_style`: `pixel_art` 962개, `rendered_icon` 150개, `illustration` 1개
- 검사 방법: 출처별 균등 표본, 기존 스타일 신호의 수치 이상치, 시각적 재검토

## 최종 분류

| style_variant | 개수 | 설명 |
|---|---:|---|
| `classic_pixel_art` | 906 | 제한된 색상과 단단한 픽셀 군집이 중심인 전통 도트 그래픽 |
| `rendered_pixel_icon` | 206 | 픽셀 형태를 유지하지만 부드러운 그라데이션·렌더 명암이 두드러지는 아이콘 |
| `rendered_illustration` | 1 | 일반 3D 렌더 일러스트로 분류되어 일러스트 폴더로 이동한 이미지 |

## 출처별 결과

| 출처 | classic | rendered | rendered_illustration |
|---|---:|---:|---:|
| `496-pixel-art-icons-for-medievalfantasy-rpg` | 143 | 0 | 0 |
| `cc0-axe-icons` | 121 | 6 | 0 |
| `cc0-ranged-icons` | 80 | 0 | 0 |
| `cc0-shield-icons` | 202 | 16 | 0 |
| `cc0-sword-icons` | 244 | 34 | 1 |
| `freepixelsweapons_itchio` | 105 | 0 | 0 |
| `shields-150-sliced` | 0 | 150 | 0 |
| `weapon-icons-0` | 11 | 0 | 0 |

## 렌더형으로 구분한 추가 범위

- 도끼: `asset_000379`~`asset_000384`
- 방패: `asset_000805`~`asset_000819`
- 방패: `asset_000748`
- 검: `asset_001078`~`asset_001082`
- 검: `asset_001091`~`asset_001114`
- 검: `asset_001022`, `asset_001023`, `asset_001028`~`asset_001030`
- `shields-150-sliced`: `asset_001321`~`asset_001470`

## 역방향 재검수 교정

- `classic_pixel_art`에서 `rendered_pixel_icon`으로 변경: `asset_000748`, `asset_001022`, `asset_001023`, `asset_001028`~`asset_001030`
- `rendered_pixel_icon`에서 `classic_pixel_art`로 변경: `asset_001121`~`asset_001126`
- 양쪽에서 6개씩 교환되어 전체 분류 개수는 유지됨

## 렌더 일러스트

- `asset_001136`: 부드러운 3D 금속 검 렌더로, `data/processed/illustration/asset_001136.png`로 이동
- `visual_style`: `illustration`
- `style_variant`: `rendered_illustration`
- 픽셀아트 train 및 split manifest에서는 제외

## 사용 지침

픽셀아트 학습·검색에는 `visual_style: pixel_art`인 962개를 사용한다. 전통 도트만 필요한 실험에서는 `style_variant: classic_pixel_art`인 906개만 선택한다. 분리한 방패 아이콘 150개는 `visual_style: rendered_icon`으로 별도 관리하지만, 세부 스타일 전체 집계에서는 `style_variant: rendered_pixel_icon` 206개에 포함된다. `asset_001136`은 통합 메타데이터에는 보존하지만 픽셀아트 학습 split에서는 제외한다.
