# 출처·라이선스 및 handedness·style 필드 추가 안내서

## 1. 현재 상태

최종 메타데이터는 다음 위치에 있습니다.

- 사람이 읽기 편한 파일: `data/metadata/final_search_assets_pretty.json`
- 프로그램용 JSONL: `data/metadata/final_search_assets.jsonl`
- 별도 출처 기록: `data/metadata/asset_sources.jsonl`

현재 최종 메타데이터에는 출처와 라이선스가 이미 `provenance` 객체 안에 병합되어 있습니다.

```json
{
  "asset_id": "asset_000085",
  "category": "axe",
  "subcategory": "hand_axe",
  "provenance": {
    "source_id": "496-pixel-art-icons-for-medievalfantasy-rpg",
    "source_url": "https://opengameart.org/content/496-pixel-art-icons-for-medievalfantasy-rpg",
    "license": "CC0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "license_status": "verified",
    "original_filename": "W_Axe002.png",
    "mapping_status": "manifest_matched"
  }
}
```

따라서 출처 정보를 다시 별도의 최상위 필드로 복사할 필요는 없습니다. 검색이나 학습 코드에서는 다음처럼 읽으면 됩니다.

```python
source_url = record["provenance"]["source_url"]
license_name = record["provenance"]["license"]
```

팀에서 반드시 단순한 최상위 구조를 요구한다면 `source_url`, `license`, `license_url`만 복사할 수 있습니다. 하지만 같은 값이 두 곳에 생기므로 나중에 서로 달라질 위험이 있습니다. 가능하면 `provenance`를 유일한 출처 기록으로 유지하는 것을 권장합니다.

## 2. 출처·라이선스 병합 방법

### 병합 기준

두 파일을 `asset_id`로 연결합니다.

- 기준 메타데이터: `final_search_assets.jsonl`
- 출처 데이터: `asset_sources.jsonl`
- 연결 키: `asset_id`

출처 레코드에서 `asset_id`를 제외한 값을 메인 레코드의 `provenance`에 넣습니다.

```python
merged = dict(metadata_record)
merged["provenance"] = {
    key: value
    for key, value in source_record.items()
    if key != "asset_id"
}
```

### 반드시 확인할 항목

병합 전후에 다음 조건을 검사합니다.

1. 메타데이터와 출처 파일이 각각 1,113개인지 확인
2. 양쪽의 `asset_id`가 모두 고유한지 확인
3. 출처 레코드가 없는 에셋이 0개인지 확인
4. 메타데이터에 없는 출처 레코드가 0개인지 확인
5. 모든 에셋에 `source_url`, `license`, `license_url`이 있는지 확인
6. 모든 `license_status`가 `verified`인지 확인
7. CC-BY 에셋은 제작자 이름과 표시 문구를 별도로 준비

현재 최종 패키지는 1,113개 모두 `provenance`가 연결되어 있고 라이선스 상태도 `verified`입니다.

## 3. handedness 필드 설계

`handedness`는 무기를 사용할 때 필요한 손의 수를 나타냅니다. 자유 문장 대신 아래 값만 사용합니다.

| 값 | 의미 |
|---|---|
| `one_handed` | 일반적으로 한 손으로 사용하는 무기 |
| `two_handed` | 일반적으로 두 손으로 사용하는 무기 |
| `versatile` | 한 손 또는 두 손으로 사용할 수 있는 무기 |
| `not_applicable` | 화살처럼 손잡고 사용하는 무기가 아님 |
| `unknown` | 이미지와 분류만으로 판단하기 어려움 |

### 1차 자동 분류 규칙

| 조건 | 권장 handedness |
|---|---|
| `dagger`, `short_dagger`, `shortsword`, `hand_axe` | `one_handed` |
| `greatsword`, `longbow`, `shortbow`, `crossbow`, `staff`, `spear` | `two_handed` |
| `longsword`, `battle_axe` | `versatile` |
| `arrow` | `not_applicable` |
| `gun`, `hammer`, `mace`, `shield`, 나머지 도끼 | 이미지와 세부분류 확인 후 결정 |

`shape_tags`에 `one_handed`나 `two_handed`가 이미 있다면 해당 값을 가장 먼저 사용합니다. 규칙이 서로 충돌하거나 형태가 불분명하면 억지로 정하지 말고 `unknown`을 사용합니다.

### 예시

```json
{
  "asset_id": "asset_000085",
  "category": "axe",
  "subcategory": "hand_axe",
  "handedness": "one_handed"
}
```

## 4. style 필드 설계

현재 모든 이미지에는 표현 방식을 나타내는 다음 필드가 이미 있습니다.

```json
"visual_style": "pixel_art"
```

`visual_style`과 새로 추가할 `style`은 역할을 구분해야 합니다.

- `visual_style`: 그림 표현 방식 (`pixel_art`)
- `style`: 무기의 시대·문화·디자인 분위기

`style`에는 다음과 같은 통제된 값만 사용하는 것을 권장합니다.

| 값 | 적용 예시 |
|---|---|
| `medieval_fantasy` | 일반적인 검, 도끼, 활, 방패, 지팡이 |
| `eastern_fantasy` | 카타나나 동양식 장식 무기 |
| `ancient_fantasy` | 고대 유물풍, 원시적 무기 |
| `tribal_fantasy` | 뼈·가죽·나무 중심의 부족풍 무기 |
| `modern_fantasy` | 총기나 기계식 무기 |
| `unknown` | 디자인 계열을 확실히 판단할 수 없음 |

현재 데이터 전체를 빠르게 정리하려면 먼저 모든 에셋에 `medieval_fantasy`를 기본값으로 넣고, 명확한 카타나·총기·부족풍 에셋만 예외 처리할 수 있습니다. 단, 검색 품질을 높이려면 캡션과 이미지를 함께 보고 수동 검수하는 편이 좋습니다.

### 예시

```json
{
  "asset_id": "asset_000085",
  "visual_style": "pixel_art",
  "style": "medieval_fantasy"
}
```

## 5. 권장 최종 구조

```json
{
  "asset_id": "asset_000085",
  "caption_en": "A silver steel pixel art hand axe with a broad rectangular blade and a wooden handle",
  "caption_ko": "넓은 사각형 은색 강철날과 나무 손잡이로 된 픽셀아트 손도끼",
  "category": "axe",
  "subcategory": "hand_axe",
  "colors": ["silver", "brown", "white"],
  "primary_color": "silver",
  "elements": [],
  "materials": ["steel", "wood"],
  "handedness": "one_handed",
  "visual_style": "pixel_art",
  "style": "medieval_fantasy",
  "provenance": {
    "source_url": "https://opengameart.org/content/496-pixel-art-icons-for-medievalfantasy-rpg",
    "license": "CC0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "license_status": "verified"
  }
}
```

## 6. 실제 적용 순서

1. 현재 메타데이터를 백업합니다.
2. `asset_id`를 기준으로 출처 파일과 메인 메타데이터의 1대1 연결을 확인합니다.
3. 출처 정보를 `provenance`에 유지합니다.
4. `shape_tags`와 `subcategory`를 우선 사용해 `handedness` 초안을 만듭니다.
5. 판단이 어려운 에셋은 `unknown`으로 표시해 수동 검수 목록으로 뺍니다.
6. 모든 에셋에 `style` 초안을 넣고 명확한 예외만 별도로 수정합니다.
7. `final_search_assets.jsonl`과 `final_search_assets_pretty.json`을 함께 갱신합니다.
8. train·validation·test 파일에도 같은 필드를 동기화합니다.
9. 각 파일의 에셋 개수와 `asset_id`가 변하지 않았는지 확인합니다.
10. `handedness`와 `style`의 누락값, 허용되지 않은 값, 한글 깨짐을 검사합니다.

## 7. 완료 기준

- 전체 에셋 수: 1,113개 유지
- 중복 `asset_id`: 0개
- 출처가 없는 에셋: 0개
- 라이선스가 없는 에셋: 0개
- `handedness` 필드 누락: 0개
- `style` 필드 누락: 0개
- 허용 목록 밖의 `handedness`와 `style`: 0개
- train·validation·test와 메인 메타데이터의 값 불일치: 0개
- UTF-8 한글 깨짐: 0개

## 8. 다음 결정 사항

실제 적용 전에 다음 두 가지를 결정해야 합니다.

1. `style`을 모든 에셋에 `medieval_fantasy`로 단순 적용할지, 디자인별로 세분화할지 결정
2. `handedness`가 애매한 방패·도끼·망치·총기류를 `unknown`으로 둘지, 이미지 검수를 추가할지 결정

안전한 방법은 자동 규칙으로 초안을 만든 뒤 애매한 항목만 별도 목록으로 출력하여 사람이 검수하는 방식입니다.
