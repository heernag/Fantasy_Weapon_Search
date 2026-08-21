# 테스트·시연용 검색 키워드

현재 데이터(1,391개)와 최종 어댑터 모델에 **실제로 질의를 넣어 보고** 결과가 좋은 것만
추린 목록입니다. 적중률은 상위 5건 중 의도한 속성을 가진 결과의 개수입니다.

측정 조건: `POST /search/text`, `top_k=5`, 기본 가중치.

---

## 1. 바로 쓸 수 있는 키워드 (적중률 순)

### 색상 + 물체 — 가장 안정적

| 질의 | 적중 | 최상위 결과 |
|---|---|---|
| `파란 검` | 5/5 | 얼음 기운이 깃든 파란 철제 소검 |
| `황금 방패` | 5/5 | 금색 픽셀아트 방패 |
| `붉은 도끼` | 5/5 | 피가 묻은 붉은 칼날의 전투도끼 |
| `은색 단검` | 5/5 | 은색 픽셀아트 카타르 |
| `보라색 검` | 5/5 | 어둠의 보라색 기운이 흐르는 양날 칼날 |
| `초록색 지팡이` | 5/5 | 초록색 가죽을 감은 손잡이 |

### 재질 + 물체

| 질의 | 적중 |
|---|---|
| `강철 대검` | 5/5 |
| `수정 지팡이` | 4/5 |
| `나무 활` | 3/5 |

### 한국어 문장형 — 단어 하나보다 훨씬 낫습니다

| 질의 | 적중 |
|---|---|
| `십자 문양이 있는 금색 방패` | 5/5 |
| `얼음 결정으로 만든 파란 대검` | 4/5 |
| `나무로 만든 갈색 장궁` | 4/5 |
| `불꽃이 타오르는 붉은 대검` | 3/5 |

### 단일 단어 — 되는 것만

| 질의 | 적중 |
|---|---|
| `방패` | 5/5 |
| `활` | 5/5 |
| `지팡이` | 3/5 |
| `단검` | 3/5 |

### 영어 질의 — 번역을 거치지 않아 안정적

| 질의 | 적중 |
|---|---|
| `golden ornate shield` | 5/5 |
| `crystal magic staff` | 5/5 |
| `a battle axe` | 5/5 |
| `a shuriken throwing star` | 5/5 |
| `wooden longbow` | 4/5 |
| `an ornate decorated shield` | 4/5 |

---

## 2. 한국어 무기 용어

한국어는 `Helsinki-NLP/opus-mt-ko-en`으로 영어 번역 후 검색합니다.

### 2-1. 교정되는 용어 (그냥 쓰면 됩니다)

`app/query_terms.py`가 아래 용어를 영어로 교정합니다. 응답의 `rewritten_query`에
어떻게 바꿔서 검색했는지 실립니다(`query_text`에는 원문이 그대로 남습니다).

| 질의 | 검색에 쓰는 영어 | 적중 |
|---|---|---|
| `표창` | `shuriken` | **5/5** |
| `수리검` | `shuriken` | **5/5** |
| `장궁` | `longbow` | **5/5** |
| `금색 창` | `gold spear` | **5/5** |
| `창` | `spear` | **4/5** |
| `번개 창` | `lightning spear` | **4/5** |
| `나무 활` | `wood bow` | **4/5** |
| `나무 장궁` | `wood longbow` | **4/5** |
| `수정 지팡이` | `crystal staff` | **5/5** |
| `철퇴` | `mace` | 3/5 |
| `석궁` | `crossbow` | 2/5 |
| `낫` | `scythe` | 0/5 |

`낫`(scythe 4개)과 `석궁`(14개)은 데이터에 그 무기가 적어 적중이 낮습니다.

교정은 **질의 전체를 영어로 바꿀 수 있을 때만** 동작합니다. 조사가 붙거나
(`창을`) 사전에 없는 단어가 섞이면 원문 그대로 번역합니다.

### 2-2. 교정하지 않는 것

문장 단위의 번역 품질은 교정 대상이 아닙니다. 아래는 그대로 두거나 필터로
지정하는 편이 정확한 경우입니다.

| 질의 | 권장 |
|---|---|
| `얼음 대검` | **그대로 쓰세요.** 원문이 5/5이고 영어로 바꾸면 2/5로 떨어집니다 |
| `전설 등급 검` | `grade=legendary` 필터 사용 |
| `양손 대검` | `handedness=two-handed` 필터 사용 |
| `동양풍 검` | `style=eastern` 필터 사용 |
| 긴 서술형 문장 | 교정 대상 아님. 짧게 `금색 창`처럼 쓰세요 |

---

## 3. 필터 조합 (번역을 거치지 않아 항상 정확)

`POST /search/text`의 `filters`에 넣습니다. 괄호 안은 실제 후보 개수입니다.

| 시연 항목 | filters | 후보 |
|---|---|---|
| 전설 등급 검 | `{"category":"sword","grade":"legendary"}` | 102 |
| 금색 방패 | `{"category":"shield","color":["gold"]}` | 157 |
| 불 속성 무기 | `{"element":"fire"}` | 50 |
| 얼음 속성 검 | `{"category":"sword","elements":["ice"]}` | 12 |
| 양손 무기 | `{"handedness":"two-handed"}` | 331 |
| 동양풍 | `{"style":"eastern"}` | 20 |
| 일러스트만 | `{"visual_style":"illustration"}` | 284 |
| 수정 지팡이 | `{"category":"staff","materials":["crystal"]}` | 29 |
| 신성 속성 방패 | `{"category":"shield","elements":["holy"]}` | 32 |

`handedness`는 `two-handed`(하이픈)와 `two_handed` 둘 다 받습니다.

> `elements`는 1,391개 중 **274개**에만 채워져 있습니다. 속성 필터를 걸면 후보가 크게
> 줄어드는 것이 정상입니다. 필드별 채움 개수는 `GET /filters/coverage`로 확인하세요.

---

## 4. 멀티모달 (이미지 + 텍스트)

`POST /search/multimodal`에 이미지와 변형 지시를 함께 보냅니다.
아래는 회색·주황 검(`asset_000982`)을 질의 이미지로 썼을 때입니다.

| 지시문 | 기본 가중치(0.4/0.6) 결과 |
|---|---|
| `금색으로 바꿔줘` | 금색 검·활로 이동 |
| `얼음 속성 파란색으로` | 파란색 검으로 이동 |
| `a red version` | 붉은 검으로 이동 |

**요령 두 가지**

1. **바꾸고 싶은 색을 지시문에 직접 넣으세요.** `얼음 속성으로 바꿔줘`처럼 색이 없으면
   원본 이미지와 비슷한 결과가 그대로 나옵니다. `얼음 속성 파란색으로`는 잘 됩니다.
2. **텍스트를 더 반영하려면 `image_weight`를 낮춥니다.** 실측 결과:

   | image_weight | `금색으로 바꿔줘` 상위 3건 |
   |---|---|
   | 0.4 (기본) | 활(금,적) · 검(흑,금) · 검(금,회) |
   | 0.2 | 검(금,회) · 검(흑,금) · 검(황,청동) |
   | 0.1 | 검(금,회) · 검(은,황) · 검(흑,금) |

   `image_weight`와 `text_weight`는 **합이 1이 되도록 함께** 보내야 합니다. 한쪽만
   보내면 400입니다.

---

## 5. 경계·오류 케이스 (QA 체크리스트)

| 케이스 | 기대 응답 |
|---|---|
| 빈 질의 (`"   "`) | 400 |
| `top_k=0` / `top_k=101` | 400 |
| `offset + top_k > 100` | 400 |
| 없는 필터 **이름** (`kind`) | 400 |
| GET 오타 파라미터 (`categoryy`) | 400 |
| `image_weight`만 전송 (합 ≠ 1) | 400 |
| 이미지가 아닌 파일 업로드 | 415 |
| 10MB 초과 이미지 | 413 |
| 없는 필터 **값** (`category=wand`) | 404 |
| 없는 에셋 (`/assets/asset_999999`) | 404 |
| 최종 번들에 없는 이미지 경로 | 404 |
| 루트 `/` | 307 → `/docs` |

---

## 6. 데이터 어휘 참조

필터에 쓸 수 있는 실제 값입니다. 전체 목록과 개수는 `GET /filters`에서 확인하세요.

- **category** (15): sword 500, shield 422, axe 176, dagger 95, bow 57, staff 40,
  arrow 29, spear 26, crossbow 14, mace 11, shuriken 7, hammer 6, scythe 4, gun 3
- **visual_style** (3): pixel_art 957, illustration 284, rendered_icon 150
- **style** (7): medieval 799, fantasy 466, holy_fantasy 51, dark_fantasy 40,
  eastern 20, nature_fantasy 12, modern 3
- **grade** (2): common 1117, legendary 274
- **handedness** (3): one_handed 1030, two_handed 331, not_applicable 30
- **colors** (25): silver 840, brown 704, black 647, gray 558, gold 442, white 440,
  red 368, blue 326, green 198, orange 184, yellow 180, bronze 174, purple 143, cyan 126
- **materials** (13): steel 1093, wood 763, leather 345, bronze 325, gold 241,
  crystal 223, cloth 64, bone 34, obsidian 19, silver 17, stone 11, chain 1
- **elements** (9, 274개에만 존재): dark 66, holy 66, fire 50, ice 34, nature 29,
  poison 12, lightning 10, water 9, wind 5
- **subcategory** (100): longsword 210, tower_shield 189, dagger 87, shortsword 69,
  round_shield 62, hand_axe 59, greatsword 53, magic_staff 40, battle_axe 39 …

---

## 7. 시연 추천 순서

1. `방패` — 한국어 단어 하나로 바로 결과 (5/5)
2. `파란 검` — 색상 결합 (5/5)
3. `십자 문양이 있는 금색 방패` — 문장형 자연어 (5/5)
4. 필터로 `전설 등급 검` 좁히기 — 후보 102건
5. 검 이미지 업로드 + `금색으로 바꿔줘` — 멀티모달
6. `image_weight` 슬라이더를 0.2로 낮춰 텍스트 반영 강화

`창`, `표창`, `장궁`처럼 번역이 깨지던 단어는 이제 그대로 써도 됩니다(2-1 참고).
`전설 등급`, `양손`, `동양풍`은 여전히 필터로 지정하세요.
