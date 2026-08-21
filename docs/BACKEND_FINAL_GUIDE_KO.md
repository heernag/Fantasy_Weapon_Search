## 1. 요구사항 대비 구현 현황

### 1-1. 역할 분담 문서 — 3번 담당 과업

| 과업 | 상태 | 구현 위치 |
|---|---|---|
| FastAPI 서버 구축 | 완료 | `app/main.py` |
| FAISS 또는 Qdrant 연동 | 완료 (FAISS `IndexFlatIP`) | `src/retrieval/search_service_adapter.py` |
| | ↳ 서버형 DB가 아니라 프로세스 내 로컬 인덱스입니다 | |
| 이미지·메타데이터 저장 | 완료 | `data/metadata/final_search_assets.jsonl`, `/images` |
| 검색 API 개발 | 완료 (요구 5개 + 확장 5개) | `app/main.py` |
| 이미지 업로드 처리 | 완료 (형식·크기·디코딩 검증) | `app/main.py`의 `read_image` |
| 카테고리·색상·속성 필터 | 완료 (11개 필드 + 별칭) | `app/repository.py`, `app/schemas.py` |
| Top-K 검색 | 완료 (1~100) | `app/schemas.py` |
| 모델 서버 연동 | 완료 — 프로세스 내 모델 연결 | `app/main.py`의 `create_search_service` |
| 검색 기록 및 응답속도 측정 | 완료 | `storage/logs/search.jsonl` |

「모델 서버 연동」은 **모델을 서비스에 연결하는 것**으로 구현했습니다. API 프로세스가
시작할 때 `WeaponSearchService`를 한 번 올리고 모든 요청에서 재사용합니다. 인수인계
문서 두 편이 모두 "서비스는 API 시작 시 한 번만 생성하고 요청마다 재사용한다"고
지시한 방식입니다.

**물리적으로 분리된 별도 모델 서버는 아닙니다.** 모델·어댑터·FAISS 인덱스가 한
객체에 묶여 있어 분리하려면 인덱스 소유권부터 다시 정해야 합니다. 분리가 필요해지면
바꿀 지점과 함께 확인할 것을 `create_search_service` 주석에 적어 두었습니다.

### 1-2. Final 과제 주제 #3 — 이미지·자연어 결합 멀티모달 검색

| 세부 과업 | 상태 |
|---|---|
| 텍스트-이미지 페어 데이터 수집 | 완료 (1,391건 전부 한국어·영어 캡션 보유) |
| 커스텀 데이터로 멀티모달 모델 학습·추론 | 완료 (train 772 / validation 94, best epoch 8) |
| 텍스트 검색 시 이미지 결과 리턴 | 완료 (`image_url`, `image_path`) |
| 이미지 검색 시 텍스트 결과 리턴 | 완료 (`result_text`, `caption_ko`, `caption_en`) |

### 1-3. Advanced 과제 주제 #2 — 벡터 검색 기반 시멘틱 서치

| 세부 과업 | 상태 |
|---|---|
| 데이터 수집 | 완료 (1,391건) |
| 벡터 DB에 데이터 저장 | 완료 — FAISS 로컬 벡터 인덱스 1,391 × 512차원 |
| 쿼리 관련 문서 추출·리턴 | 완료 |
| 세부검색 필터링 | 완료 |
| 리턴된 문서 페이징 | 완료 (`offset`) |

---

## 2. 시스템 구성

```
요청
 └─ app/main.py            입력 검증, 라우팅, 페이지 범위 확인
     └─ app/official_search.py   질의 재작성, 필터 표기 정규화, 로그, 응답 조립
         └─ src/retrieval/search_service_adapter.py   커스텀 어댑터 + FAISS 검색
             └─ src/retrieval/search_service.py       OpenCLIP 베이스라인(상속 원본)
     └─ app/repository.py   메타데이터 조회, 필터 어휘 사전
     └─ app/service_manifest.py   기동 시 번들 무결성 검증
```

`src/retrieval/`의 두 파일은 **1번 AI 담당이 작성해 넘겨준 것이며, 이번 백엔드
작업에서는 한 줄도 수정하지 않았습니다.** FAISS 검색과 어댑터 적용은 인수인계 시점에
이미 그 안에 구현돼 있었습니다. 이번 작업에서 추가한 페이징, 질의 용어 교정, 필터
표기 정규화는 **전부 `app/` 계층**에서 처리했습니다.

> 2번 파트 완료 시점의 스냅샷과 비교하면 이 두 파일이 달라 보이는데, 그 차이는
> 1번 담당의 어댑터 병합(원격 `main`의 `fd35d0a`)에서 생긴 것입니다.

### 모델과 데이터

| 항목 | 값 |
|---|---|
| 베이스 모델 | OpenCLIP `ViT-B-16` / `laion2b_s34b_b88k` |
| 커스텀 학습 | 이미지·텍스트 512차원 residual adapter (best epoch 8) |
| 인덱스 | FAISS `IndexFlatIP`, 1,391 벡터 × 512차원 (로컬 인덱스) |
| 결합 검색 기본 가중치 | 이미지 `0.4` / 텍스트 `0.6` |
| 한국어 처리 | `Helsinki-NLP/opus-mt-ko-en` 번역 후 검색 |
| 에셋 | 1,391개 (pixel_art 957 / illustration 284 / rendered_icon 150) |

### 기동 시 무결성 검증

서버가 시작할 때 `storage/indexes/service_manifest.json`과 실제 파일의 sha256,
asset_id 순서, 벡터 개수를 대조합니다. 하나라도 어긋나면 **기동에 실패합니다.**
잘못된 인덱스로 조용히 서비스되는 것을 막기 위한 장치입니다.

검증 대상: 어댑터 가중치, 어댑터 임베딩, asset_ids, 메타데이터, FAISS 인덱스.

---

## 3. 실행 방법

### 3-1. 설치

```
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> **`requirements-ai.txt`는 API 환경에 설치하지 마세요.**
> 자세한 이유는 [7. 의존성 주의사항](#7-의존성-주의사항)을 참고하세요.

### 3-2. 서버 실행

```
run_server.cmd
```

| 주소 | 용도 |
|---|---|
| `http://127.0.0.1:8000` | API 문서로 이동 |
| `http://127.0.0.1:8000/docs` | Swagger UI |
| `http://127.0.0.1:8000/health` | 상태 확인 |

중지는 `Ctrl+C`입니다. 기동에 실패하면 창이 유지되며 원인별 조치 방법이 출력됩니다.

### 3-3. 설정

경로와 옵션은 `.env.example`의 `FWS_*` 환경변수로 바꿉니다. 상대경로는 저장소 루트
기준으로 해석되므로 폴더를 옮겨도 그대로 동작합니다.

프론트엔드를 붙일 때는 **`FWS_CORS_ORIGINS`에 origin을 반드시 지정**해야 합니다.
기본값이 비어 있어 CORS가 꺼져 있습니다.

### 3-4. Docker

```
docker build -t fantasy-weapon-search .
docker run -p 8000:8000 -v fws-cache:/app/.cache fantasy-weapon-search
```

`-v`로 `/app/.cache`를 붙이면 컨테이너를 다시 만들어도 모델 약 1.7GB를 다시 받지
않습니다. 검색 서비스가 캐시 경로를 하드코딩하고 있어 `FWS_MODEL_CACHE` 같은
환경변수로는 위치를 바꿀 수 없습니다(자세한 설명은 `Dockerfile` 주석 참고).

---

## 4. API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/search/text` | 자연어 검색 (JSON) |
| GET | `/search/text` | 자연어 검색 (쿼리스트링) |
| POST | `/search/image` | 이미지 검색 (multipart) |
| POST | `/search/multimodal` | 이미지 + 텍스트 결합 검색 |
| GET | `/assets/{asset_id}` | 단일 에셋 메타데이터 |
| GET | `/filters` | 필터 필드별 값 목록과 값별 에셋 수 |
| GET | `/filters/coverage` | 필터 필드별로 값이 채워진 에셋 수 |
| GET | `/health` | 에셋·벡터 수, 모델, 서비스 버전 |
| GET | `/images/{경로}` | 최종 메타데이터에 있는 이미지만 제공 |
| GET | `/` | `/docs`로 이동 |

### 4-1. 요청

```json
POST /search/text
{
  "query": "파란 얼음 검",
  "top_k": 10,
  "offset": 0,
  "filters": { "category": "sword", "colors": ["blue"] }
}
```

- `top_k` 1~100, `offset` 0 이상, **`offset + top_k`는 100 이하**
  (검색 서비스가 한 번에 매기는 순위 상한이 100입니다)
- 이미지 계열은 multipart이며 `image` 파일이 필수입니다.
  업로드는 PNG·JPEG·WEBP, 10MB 이하만 받습니다.
- `image_weight`와 `text_weight`는 **합이 1이 되도록 함께** 보내야 합니다.

### 4-2. 응답

```json
{
  "search_type": "text",
  "query_type": "text",
  "query_text": "파란 얼음 검",
  "rewritten_query": null,
  "translated_text": "The blue ice blade.",
  "image_weight": null,
  "text_weight": null,
  "top_k": 10,
  "offset": 0,
  "candidate_count": 500,
  "elapsed_ms": 82.588,
  "search_elapsed_ms": 80.78,
  "results": [ { "asset_id": "...", "score": 0.71, "...": "..." } ]
}
```

- `candidate_count`는 필터를 통과한 **전체 개수**입니다. 페이징 UI의 총량으로 씁니다.
- `elapsed_ms`는 요청 전체, `search_elapsed_ms`는 검색 구간 시간입니다.
- 결과 항목에는 `image_url`, `result_text`, `caption_ko/en`, `category`,
  `subcategory`, `colors`, `materials`, `elements`, `shape_tags`, `grade`,
  `handedness`, `style`, `source`, `license`와 원본 `metadata`가 들어갑니다.
- 결합 검색은 `combined_score`·`image_score`·`text_score`를 함께 줍니다.

### 4-3. 오류 응답

| 상황 | 코드 |
|---|---|
| 빈 질의, `top_k` 범위 밖, `offset + top_k > 100` | 400 |
| 지원하지 않는 파라미터·필터 이름, 별칭 충돌 | 400 |
| 가중치 합이 1이 아님 | 400 |
| PNG·JPEG·WEBP가 아닌 파일 | 415 |
| 10MB 초과 이미지 | 413 |
| 조건에 맞는 결과 없음, 없는 에셋, 번들 밖 이미지 | 404 |

---

## 5. 필터

단일값 `visual_style` `category` `subcategory` `primary_color` `grade` `style` `handedness`
목록값 `colors` `materials` `elements` `shape_tags`
호환 별칭 `color`(=`colors`) `element`(=`elements`) `categories` `styles`

- 목록 필터에 값을 여러 개 주면 **모두** 가진 에셋만 후보가 됩니다.
- 값 표기는 API 경계에서 정규화합니다. 대소문자와 `-`/`_`/공백 차이를 흡수하므로
  `two-handed`, `Two Handed`, `two_handed`가 같은 결과를 냅니다.
- 별칭은 GET·POST·이미지 폼·멀티모달 폼 네 경로에서 동일하게 동작합니다.
- 존재하지 않는 필터 **이름**은 400, 존재하지 않는 **값**은 결과 없음(404)입니다.

### 데이터 채움 현황

`elements`만 1,391개 중 **274개(19.7%)** 에 채워져 있습니다. 속성 필터를 걸면 후보가
크게 줄어드는 것이 정상입니다. `shape_tags`는 1,378개(99.1%), 나머지 필드는 전부
1,391개입니다. 필드별 수치는 `GET /filters/coverage`로 확인할 수 있으며,
프론트엔드는 이 값으로 "값이 있는 에셋만 검색됨"을 안내할 수 있습니다.

---

## 6. 한국어 질의 처리

한국어는 번역 후 검색합니다. 다만 아래 무기 용어는 번역기가 다른 뜻으로 옮기기
때문에, 번역을 거치지 않고 영어 용어로 바로 검색하도록 `app/query_terms.py`에
사전을 두었습니다.

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

**질의 전체를 영어로 바꿀 수 있을 때만** 교정합니다. 조건에 맞지 않으면 원문 그대로
번역합니다. 교정한 경우 응답의 `rewritten_query`에 바뀐 질의가 실리고,
`query_text`에는 사용자가 보낸 원문이 그대로 남습니다.

문장 단위의 번역 품질은 교정 대상이 아닙니다. `전설 등급`, `양손`, `동양풍` 같은
속성은 텍스트보다 **필터로 지정하는 편이 정확합니다.**

검증된 시연용 키워드와 오류 케이스 목록은 `docs/TEST_KEYWORDS_KO.md`에 있습니다.

---

## 7. 의존성 주의사항

`requirements.txt`와 `requirements-ai.txt`는 **numpy 핀이 서로 다릅니다.**

| 파일 | numpy | 용도 |
|---|---|---|
| `requirements.txt` | **1.26.4** | API 서버 (현재 검증된 조합) |
| `requirements-ai.txt` | 2.4.4 | 학습·임베딩 파이프라인 |

API 환경에서 `requirements-ai.txt`를 나중에 설치하면 numpy가 2.x로 올라가고,
1.x에 맞춰 빌드된 `faiss-cpu`와 `torch`가 깨질 수 있습니다.

**그런데 `requirements-ai.txt`가 추가로 주는 패키지는 `tqdm` 하나뿐입니다.**
API에 필요한 torch·open-clip·transformers·faiss는 이미 `requirements.txt`에 모두
들어 있습니다. 즉 **API 서버는 `requirements-ai.txt`를 설치할 이유가 없습니다.**

AI 담당자의 인수인계 메모 원문에는 "필요하면 AI 패키지를 설치해주세요
`pip install -r requirements-ai.txt`"라고 적혀 있는데, 그대로 따르면 위 문제가
생깁니다. 학습 스크립트(`src/training`, `src/embedding`)를 돌려야 한다면 **API와
분리된 가상환경**을 쓰세요.

정리 방향은 팀에서 정하면 됩니다 — 한쪽 핀으로 통일하거나,
`requirements-ai.txt`에서 numpy 핀을 빼는 편이 안전합니다.

---

## 8. 운영

### 검색 기록

모든 검색은 `storage/logs/search.jsonl`에 한 줄씩 기록됩니다.

```
timestamp, query_type, detail, translated_text, rewritten_query,
filters, top_k, offset, result_count, elapsed_ms, search_elapsed_ms,
status_code, service_version
```

`filters`에는 **검색에 실제로 적용된 값**이 들어갑니다. 별칭과 표기를 정규화한 뒤의
값이라 로그만으로 결과를 재현할 수 있습니다.

### 이미지 제공

`/images`는 최종 메타데이터에 있는 1,391개만 제공합니다. `data/processed` 아래에
남아 있는 작업 파일은 404입니다. 경로 탈출 시도도 404로 막힙니다.

### 인덱스 재생성

```
.venv\Scripts\python.exe scripts\build_final_index.py
```

`scripts/build_index.py`는 **베이스라인 임베더**로 같은 파일을 덮어쓰기 때문에 실행
진입점을 주석 처리해 막아 두었습니다. 인덱스를 다시 만들 때는 반드시
`build_final_index.py`를 쓰세요.

### 테스트

```
.venv\Scripts\python.exe -m pytest -q
```

현재 85개 전부 통과합니다. API 계약, 필터 정규화, 페이징, 번들 무결성, 배포 계약
(Dockerfile이 필요한 디렉터리를 복사하는지)까지 확인합니다.

---

## 9. 규격을 따르지 않기로 한 결정

나중에 "문서와 다르다"는 이유로 되돌리지 않도록 근거를 남깁니다. 상세한 판단 근거와
되돌리는 절차는 각 코드 주석에 있습니다.

| 항목 | 결정 | 근거 | 주석 위치 |
|---|---|---|---|
| `element`/`color` 응답 형태 | 규격의 단일 문자열 대신 **배열 유지** | 값이 둘 이상인 에셋에서 데이터가 잘림. `color`는 규격에서도 배열이라 일관성이 깨짐. 입력 필터는 규격대로 보내도 동작 | `app/schemas.py`의 `SearchHit` |
| `categories`/`styles` 별칭 | 폐기하지 않고 **네 경로 모두에서 수용** | 폐기하면 쓰던 클라이언트가 깨지지만, 받아주는 쪽은 순수 추가라 위험이 없음 | `app/main.py`의 `LEGACY_FILTER_NAMES` |
| 모델 로딩 방식 | 별도 서버 없이 **프로세스 내 로딩** | 인수인계 문서 두 편이 "시작 시 한 번 생성해 재사용"을 지시. 모델·어댑터·인덱스가 한 객체에 묶여 있음 | `app/main.py`의 `create_search_service` |

---

## 10. 남은 작업과 담당

| 항목 | 담당 | 내용 |
|---|---|---|
| 모델 서버 분리 (선택) | 1번 AI | 물리적으로 분리된 모델 서버가 필요해지면 논의 |
| numpy 핀 통일 | 팀 | 7절 참고 |
| 프론트엔드 연동 | 4번 프론트 | `FWS_CORS_ORIGINS` 지정 필요 |
| Docker Compose | 4번 배포 | 현재 요구사항 문서에는 없음. 프론트와 함께 묶을 때 필요하면 추가 |

---

## 11. 참고 문서

| 문서 | 내용 |
|---|---|
| `docs/TEST_KEYWORDS_KO.md` | 검증된 시연용 키워드, 필터 조합, 멀티모달 요령, QA 오류 케이스 |
| `docs/CUSTOM_ADAPTER_HANDOFF_KO.md` | AI 담당의 최종 어댑터 문서. 모델·성능 수치의 기준 |
| `docs/AI_SEARCH_API_HANDOFF_KO.md` | 어댑터 이전의 베이스라인 문서. 서비스 사용법과 필터 설명은 유효 |
| `docs/BACKEND_VECTORDB_HANDOFF_KO.md` | 인수인계용 요약본 |
| `README.md` | 데이터셋 구성과 출처·라이선스 |
