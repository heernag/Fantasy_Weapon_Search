# 백엔드 기능 정리

판타지 무기 멀티모달 검색 API가 제공하는 기능을 동작 단위로 정리했습니다.
설치·실행과 운영 방법은 `docs/BACKEND_FINAL_GUIDE_KO.md`를, 검증된 질의 예시는
`docs/TEST_KEYWORDS_KO.md`를 참고하세요.

---

## 1. 검색

세 가지 검색 방식이 있습니다. 모두 같은 벡터 공간(512차원)에서 동작하고 같은 형식으로
응답합니다. 벡터 검색은 FAISS `IndexFlatIP` **로컬 인덱스**로 수행합니다(서버형 벡터
DB가 아니라 API 프로세스 안에서 도는 인덱스입니다).

### 1-1. 텍스트 검색

자연어 문장을 벡터로 바꿔 이미지와 대조합니다.

| | |
|---|---|
| 경로 | `POST /search/text` (JSON) · `GET /search/text` (쿼리스트링) |
| 입력 | `query` (1~500자), `top_k`, `offset`, `filters` |
| 출력 | 유사도 내림차순 이미지 목록 |

- 한국어 질의는 영어로 번역한 뒤 검색합니다(3절).
- 영어 질의는 번역 단계를 거치지 않습니다.
- 두 경로는 같은 결과를 냅니다. GET은 브라우저·링크 공유용, POST는 필터가 복잡할 때 씁니다.

### 1-2. 이미지 검색

업로드한 이미지와 비슷한 이미지를 찾습니다.

| | |
|---|---|
| 경로 | `POST /search/image` (multipart) |
| 입력 | `image` (필수), `top_k`, `offset`, `include_self`, 필터 |
| 출력 | 유사도 내림차순 이미지 목록 |

**같은 이미지 제외** — 업로드한 파일의 SHA-256이 데이터셋의 에셋과 일치하면 그 에셋을
결과에서 뺍니다. 자기 자신이 1위로 올라와 나머지를 밀어내는 것을 막기 위해서입니다.
`include_self=true`를 보내면 포함합니다.

```
include_self=false  ->  asset_000059, asset_000114, asset_000438
include_self=true   ->  asset_000057(score 1.0), asset_000059, asset_000114
```

### 1-3. 멀티모달 결합 검색

이미지와 문장을 함께 넣어 "이 이미지에서 이렇게 바뀐 것"을 찾습니다.

| | |
|---|---|
| 경로 | `POST /search/multimodal` (multipart) |
| 입력 | `image` (필수), `query` (필수), `image_weight`, `text_weight`, `top_k`, `offset`, 필터 |
| 출력 | 결합 점수 내림차순 목록 + 개별 점수 |

두 벡터를 가중 합산해 정규화한 벡터로 검색합니다. 기본값은 이미지 `0.4` / 텍스트 `0.6`
입니다. 결과에는 최종 점수와 함께 개별 유사도가 들어갑니다.

```json
{ "score": 0.513, "combined_score": 0.513,
  "image_score": 0.7589, "text_score": 0.2737 }
```

**가중치 조절** — `image_weight`를 낮출수록 문장의 지시가 강하게 반영됩니다.
두 값은 **합이 1이 되도록 함께** 보내야 하며, 어긋나면 400을 돌려줍니다.
한쪽만 보내 조용히 재조정되면 요청한 비율과 실제 검색 비율이 달라지기 때문입니다.

---

## 2. 필터

검색 후보를 속성으로 좁힙니다. 세 검색 방식 모두에서 같은 필터를 씁니다.

### 2-1. 필터 필드

| 종류 | 필드 | 동작 |
|---|---|---|
| 단일값 | `visual_style` `category` `subcategory` `primary_color` `grade` `style` `handedness` | 정확히 일치 |
| 목록값 | `colors` `materials` `elements` `shape_tags` | 지정한 값을 **모두** 가진 에셋만 |
| 호환 별칭 | `color`(=`colors`) `element`(=`elements`) `categories`(=`category`) `styles`(=`style`) | 정식 필드로 접어서 처리 |

별칭은 GET·POST·이미지 폼·멀티모달 폼 **네 경로에서 동일하게** 동작합니다.
정식 이름과 별칭에 서로 다른 값을 함께 보내면 충돌로 400입니다.

### 2-2. 값 표기 정규화

필터 값은 API 경계에서 실제 메타데이터 표기로 맞춥니다. 검색 판정이 정확 일치라
표기가 조금만 달라도 결과가 0건이 되기 때문입니다.

- 대소문자 무시 — `Sword` → `sword`
- `-` / `_` / 공백을 같은 것으로 취급 — `two-handed`, `Two Handed` → `two_handed`
- 메타데이터에 없는 값은 바꾸지 않고 그대로 넘깁니다 (결과 없음으로 처리)

### 2-3. 필터 값 조회

| 경로 | 내용 |
|---|---|
| `GET /filters` | 필드별로 실제 존재하는 값과 그 값을 가진 에셋 수. 빈도 내림차순 |
| `GET /filters/coverage` | 필드별로 값이 채워진 에셋 수 |

```json
GET /filters
{ "category": [ {"value": "sword", "count": 500},
                {"value": "shield", "count": 422}, ... ] }
```

`/filters`는 모든 키가 같은 모양(값 목록)이라 순회해서 필터 UI를 만들 수 있습니다.
모양이 다른 커버리지 정보는 별도 경로로 분리했습니다.

`elements`처럼 일부 에셋에만 채워진 속성은 필터를 거는 순간 후보가 크게 줄어듭니다.
`/filters/coverage`로 그 비율을 확인해 UI에 안내할 수 있습니다.

---

## 3. 한국어 질의 처리

### 3-1. 번역

질의에 한글이 있으면 `Helsinki-NLP/opus-mt-ko-en`으로 영어 번역한 뒤 검색합니다.
번역 결과는 응답의 `translated_text`에 실립니다. 영어 질의는 번역을 거치지 않아
이 값이 `null`입니다.

### 3-2. 무기 용어 교정

아래 용어는 번역을 거치지 않고 영어 용어로 바로 검색합니다. 번역기가 다른 뜻으로
옮기는 단어들이라 사전에 등록해 두었습니다.

| 한국어 | 검색에 쓰는 영어 |
|---|---|
| `창` | `spear` |
| `석궁` | `crossbow` |
| `장궁` | `longbow` |
| `낫` | `scythe` |
| `표창` · `수리검` | `shuriken` |
| `철퇴` | `mace` |
| `곤봉` | `club` |
| `수정` | `crystal` |
| `나무` | `wood` |

**동작 조건** — 질의의 모든 토큰이 사전에 있고, 그중 위 용어가 하나 이상일 때만
전체를 영어로 바꿉니다. 조건에 맞지 않으면 원문 그대로 번역합니다. 사전은
`app/query_terms.py`에 있습니다.

**응답 표시** — 교정한 경우 `rewritten_query`에 바뀐 질의가 실리고, `query_text`에는
사용자가 보낸 원문이 그대로 남습니다. 번역을 거치지 않으므로 `translated_text`는
`null`입니다.

```json
{ "query_text": "번개 창", "rewritten_query": "lightning spear",
  "translated_text": null }
```

`scythe`(4개), `shuriken`(7개), `mace`(11개)처럼 데이터에 적은 무기는 교정 후에도
결과 수가 적습니다.

문장 단위의 번역 품질은 교정 대상이 아닙니다.

---

## 4. 페이징

세 검색 방식 모두 `top_k`(페이지 크기)와 `offset`(건너뛸 개수)을 받습니다.

- `top_k` 1~100, `offset` 0 이상, **`offset + top_k`는 100 이하**
- 응답의 `candidate_count`가 필터를 통과한 전체 개수라 마지막 페이지를 계산할 수 있습니다
- 페이지를 나눠 받아도 한 번에 받은 결과와 순서가 같습니다

```
top_k=4, offset=0  +  top_k=4, offset=4   ==   top_k=8, offset=0
```

`offset`이 후보 수를 넘으면 빈 목록과 함께 200을 돌려줍니다.

---

## 5. 결과 조회

### 5-1. 에셋 상세

`GET /assets/{asset_id}` — 단일 에셋의 전체 메타데이터와 이미지 URL을 돌려줍니다.

### 5-2. 이미지 제공

`GET /images/{경로}` — 검색 결과의 `image_url`이 가리키는 경로입니다.
**최종 메타데이터에 등록된 이미지만** 제공하며, 작업 폴더에 남아 있는 파일이나
경로 탈출 시도는 404입니다.

---

## 6. 응답 형식

### 6-1. 공통 필드

| 필드 | 내용 |
|---|---|
| `search_type` · `query_type` | 검색 종류 (`text` / `image` / `multimodal`) |
| `query_text` | 사용자가 보낸 질의 원문 |
| `rewritten_query` | 용어 교정으로 다시 쓴 질의. 없으면 `null` |
| `translated_text` | 번역 결과. 영어 질의나 용어 교정을 거친 경우 `null` |
| `image_weight` · `text_weight` | 결합 검색에 적용된 가중치 |
| `top_k` · `offset` | 요청한 페이지 |
| `candidate_count` | 필터를 통과한 전체 개수 |
| `elapsed_ms` · `search_elapsed_ms` | 요청 전체 / 검색 구간 소요 시간 |
| `results` | 결과 목록 |

### 6-2. 결과 항목

| 분류 | 필드 |
|---|---|
| 식별·점수 | `asset_id` `score` `combined_score` `image_score` `text_score` |
| 이미지 | `image_url`(제공 경로) `image_path`(저장소 상대경로) |
| 텍스트 | `result_text` `caption_ko` `caption_en` |
| 속성 | `category` `subcategory` `visual_style` `style` `grade` `handedness` `primary_color` `colors` `materials` `elements` `shape_tags` |
| 별칭 | `color`(=`colors`) `element`(=`elements`) |
| 출처 | `source` `source_url` `license` |
| 원본 | `metadata` (에셋의 전체 메타데이터) |

`result_text`는 한국어 캡션을 우선하고 없으면 영어 캡션을 씁니다.
이미지 검색에서 텍스트 결과를 받는 통로입니다.

---

## 7. 입력 검증

잘못된 요청을 조용히 무시하지 않고 원인을 알려줍니다.

| 검증 | 응답 |
|---|---|
| 빈 질의, `top_k` 범위 밖, `offset + top_k > 100` | 400 |
| 선언되지 않은 파라미터 이름 (오타 포함) | 400 |
| 별칭과 정식 이름의 값 충돌, 빈 필터 값 | 400 |
| 가중치 합이 1이 아님 | 400 |
| PNG·JPEG·WEBP가 아닌 파일 | 415 |
| 10MB 초과 이미지 | 413 |
| 손상되어 열 수 없는 이미지 | 400 |
| 조건에 맞는 결과 없음 | 404 |
| 없는 에셋, 등록되지 않은 이미지 경로 | 404 |

업로드 이미지는 확장자가 아니라 **실제로 디코딩해서** 검증합니다.

---

## 8. 운영 기능

### 8-1. 상태 확인

`GET /health` — 적재된 에셋 수, 벡터 수, 벡터 차원, 모델 이름, 서비스 버전을 돌려줍니다.
검색 서비스와 메타데이터가 같은 번들인지 확인하는 용도로 씁니다.

### 8-2. 검색 기록

모든 검색을 `storage/logs/search.jsonl`에 한 줄씩 남깁니다.

```
timestamp, query_type, detail, translated_text, rewritten_query,
filters, top_k, offset, result_count, elapsed_ms, search_elapsed_ms,
status_code, service_version
```

`filters`에는 별칭과 표기를 정규화한 **실제 적용 값**이 들어가, 로그만으로 결과를
재현할 수 있습니다. 결과가 없어 404가 나간 요청도 기록됩니다.

### 8-3. 응답 시간 측정

`elapsed_ms`는 요청이 서버에 도착한 시점부터, `search_elapsed_ms`는 검색 호출
구간만 잽니다. 두 값의 차이로 전처리·후처리 비용을 볼 수 있습니다.

### 8-4. 기동 시 번들 검증

서버가 시작할 때 어댑터 가중치·임베딩·asset_ids·메타데이터·FAISS 인덱스의 SHA-256과
개수, asset_id 순서를 manifest와 대조합니다. 하나라도 어긋나면 **기동에 실패합니다.**
잘못된 인덱스로 검색이 조용히 이상해지는 것을 막습니다.

### 8-5. 문서 페이지

`GET /` → `/docs`로 이동합니다. `GET /docs`는 Swagger UI로, 모든 엔드포인트를
브라우저에서 바로 호출해 볼 수 있습니다.

---

## 9. 엔드포인트 요약

| 메서드 | 경로 | 기능 |
|---|---|---|
| `POST` | `/search/text` | 자연어 검색 |
| `GET` | `/search/text` | 자연어 검색 (쿼리스트링) |
| `POST` | `/search/image` | 이미지 검색 |
| `POST` | `/search/multimodal` | 이미지 + 텍스트 결합 검색 |
| `GET` | `/assets/{asset_id}` | 에셋 상세 |
| `GET` | `/filters` | 필터 값 목록 |
| `GET` | `/filters/coverage` | 필터 채움 현황 |
| `GET` | `/images/{경로}` | 이미지 제공 |
| `GET` | `/health` | 상태 확인 |
| `GET` | `/` | 문서로 이동 |
