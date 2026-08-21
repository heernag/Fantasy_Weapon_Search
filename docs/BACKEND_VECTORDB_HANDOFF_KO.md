# 3번 백엔드·Vector DB 최종 인수인계

검색 API가 어떤 모델과 인덱스를 쓰는지, 프론트엔드가 무엇을 호출하면 되는지를
정리한 백엔드 담당 문서입니다.

## 1. 최종 검색 서비스

API는 커스텀 어댑터 서비스 하나만 사용합니다.

```python
from src.retrieval.search_service_adapter import WeaponSearchService
```

`src.retrieval.search_service.WeaponSearchService`는 어댑터 학습 이전의
베이스라인이며 API에서 직접 import하지 않습니다. 어댑터 서비스가 이 클래스를
상속해 인코딩 단계만 교체하므로, 메서드 이름과 응답 형식은 두 쪽이 같습니다.

서비스는 무거운 모델과 임베딩을 메모리에 올리므로 서버 시작 시 한 번만 만들고
모든 요청에서 재사용합니다. 생성 위치는 `app/main.py`의 lifespan입니다.

## 2. 서비스가 읽는 파일

| 용도 | 경로 |
|---|---|
| 어댑터 가중치 | `models/clip_adapter_vit_b16/best_adapter.pt` |
| 어댑터 이미지 임베딩 | `embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/image_embeddings.npy` |
| 임베딩 asset_id 순서 | `embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/asset_ids.json` |
| FAISS 인덱스 | `storage/indexes/weapons.faiss` |
| 인덱스 asset_id 순서 | `storage/indexes/weapon_ids.json` |
| 검색 메타데이터 | `data/metadata/final_search_assets.jsonl` |
| 번들 검증 manifest | `storage/indexes/service_manifest.json` |

`storage/indexes/weapons.faiss`는 베이스라인이 아니라 **어댑터 임베딩으로 빌드된
인덱스**입니다(`scripts/build_final_index.py`). 서버는 시작할 때
`service_manifest.json`의 sha256과 asset_id 순서를 대조해 모델·임베딩·인덱스·
메타데이터가 같은 번들인지 확인하고, 어긋나면 기동에 실패합니다.

## 3. 검색 범위와 학습 범위가 다르다

주의해야 할 차이입니다.

- 어댑터 학습·모델 선택에 쓴 데이터는 **pixel_art split뿐**입니다(train 772쌍,
  validation 94쌍, best epoch 8).
- 서비스 인덱스는 **최종 메타데이터 1,391개 전체**입니다
  (pixel_art 957 + illustration 284 + rendered_icon 150).

즉 illustration과 rendered_icon 434개는 어댑터가 학습하지 않은 스타일인데도
검색 결과에 함께 나옵니다. 성능 수치를 인용할 때는 이 범위 차이를 함께 밝히고,
스타일별 품질을 비교하려면 `visual_style` 필터로 나눠서 확인하세요.

## 4. 엔드포인트

| 메서드 | 경로 | 비고 |
|---|---|---|
| POST | `/search/text` | JSON 본문 |
| GET | `/search/text` | 쿼리 문자열 |
| POST | `/search/image` | multipart, `image` 필수 |
| POST | `/search/multimodal` | multipart, `image` + `query` |
| GET | `/assets/{asset_id}` | 단일 에셋 메타데이터 |
| GET | `/filters` | 필터 필드별 값 목록과 값별 에셋 수 |
| GET | `/filters/coverage` | 필터 필드별로 값이 채워진 에셋 수 |
| GET | `/health` | 에셋 수, 벡터 수, 모델, service_version |
| GET | `/images/{경로}` | 최종 메타데이터에 있는 이미지만 제공 |

결합 검색 기본 가중치는 이미지 `0.4` / 텍스트 `0.6`이고, 한국어 질의는
`Helsinki-NLP/opus-mt-ko-en`으로 영어 번역 후 검색합니다. `image_weight`와
`text_weight`를 바꿀 때는 두 값을 함께 보내야 하며 합이 1이어야 합니다. 합이
맞지 않으면 400입니다.

### 페이징

세 검색 엔드포인트 모두 `top_k`(페이지 크기)와 `offset`(건너뛸 개수)을 받습니다.
응답의 `candidate_count`가 필터를 통과한 전체 개수이므로 마지막 페이지를 계산할
수 있습니다. 검색 서비스가 한 번에 매기는 순위가 100개까지라
`offset + top_k`는 100 이하여야 하고, 넘으면 400입니다.

## 5. 필터

단일값: `visual_style`, `category`, `subcategory`, `primary_color`, `grade`,
`style`, `handedness`
목록값: `colors`, `materials`, `elements`, `shape_tags`
별칭: `color`(=`colors`), `element`(=`elements`)

- 값 표기는 API 경계에서 정규화합니다. 대소문자와 `-`/`_`/공백 차이를 흡수하므로
  `two-handed`, `Two Handed`, `two_handed`가 모두 같은 결과를 냅니다.
- 목록 필터에 여러 값을 주면 그 값을 **모두** 가진 에셋만 후보가 됩니다.
- 선언되지 않은 파라미터 이름은 무시하지 않고 400으로 돌려줍니다.
- `elements`는 1,391개 중 274개에만 채워져 있습니다. `/filters/coverage`가
  필드별 채움 개수를 주니, 필터 UI에서 "값이 있는 에셋만 검색됨"을 표시하세요.
  `/filters`는 모든 키가 값 목록으로 모양이 같아 그대로 순회할 수 있습니다.
- `categories`/`styles` 호환 별칭은 GET·POST·폼 네 곳에서 동일하게 동작합니다.

## 6. 응답과 로그

- `image_path`는 저장소 루트 기준 상대경로, `image_url`은 `/images/...` 형태입니다.
- `/images`는 최종 메타데이터에 있는 파일만 제공합니다. `data/processed` 아래에
  남아 있는 작업 파일은 404입니다.
- `elapsed_ms`는 요청 전체, `search_elapsed_ms`는 검색 구간 시간입니다.
- 검색 기록은 `storage/logs/search.jsonl`에 남고, `filters`에는 별칭과 표기를
  정규화한 **실제 적용 값**이 기록됩니다.

## 7. 실행

```
pip install -r requirements.txt
run_server.cmd
```

**`requirements-ai.txt`는 API 서버에 설치하지 마세요.** 인수인계 메모에는 "필요하면
AI 패키지를 설치"라고 적혀 있지만, API에 필요한 torch·open-clip·transformers·faiss는
이미 `requirements.txt`에 모두 들어 있습니다. 두 파일은 numpy 핀이 다릅니다
(`requirements.txt` 1.26.4 / `requirements-ai.txt` 2.4.4). AI 쪽을 나중에 설치하면
numpy가 2.x로 올라가고, 1.x에 맞춰 빌드된 faiss-cpu·torch가 깨질 수 있습니다.
`requirements-ai.txt`가 추가로 주는 패키지는 `tqdm` 하나뿐이며, 이는 학습·임베딩
파이프라인(`src/training`, `src/embedding`)에서만 씁니다. 학습을 돌려야 한다면
API와 분리된 가상환경을 쓰세요.

`http://127.0.0.1:8000/docs`에서 Swagger UI로 확인할 수 있습니다. 경로와 캐시
위치는 `.env.example`의 `FWS_*` 환경변수로 바꿉니다. CORS는 기본이 꺼져 있으므로
프론트엔드 origin을 `FWS_CORS_ORIGINS`에 명시해야 합니다.

## 8. 참고 문서

- `docs/BACKEND_FINAL_GUIDE_KO.md` — **최종 가이드.** 요구사항 대비 구현 현황,
  시스템 구성, 실행 방법, API 전체 명세, 필터, 한국어 질의 처리, 의존성 주의사항,
  운영, 설계 결정 근거를 한 문서에 모았습니다. 이 문서는 요약본입니다.
- `docs/TEST_KEYWORDS_KO.md` — 실제 데이터로 적중률을 측정해 추린 테스트·시연용
  검색 키워드, 필터 조합, 멀티모달 문구, 오류 케이스 체크리스트. 시연 대본을
  쓰기 전에 확인하세요.

- `docs/CUSTOM_ADAPTER_HANDOFF_KO.md` — AI 담당자의 최종 어댑터 문서. 모델·성능
  수치는 이 문서가 기준입니다.
- `docs/AI_SEARCH_API_HANDOFF_KO.md` — 어댑터 이전의 베이스라인 문서. 서비스
  사용법과 필터 설명은 여전히 유효하지만, 모델과 성능 수치는 위 문서를 따릅니다.

## 9. 규격을 따르지 않기로 한 부분

나중에 "규격과 다르다"는 이유로 되돌리지 않도록 근거를 남깁니다. 각 항목의
자세한 판단 근거와 되돌리는 절차는 코드 주석에 적어 두었습니다.

| 항목 | 결정 | 근거 | 주석 위치 |
|---|---|---|---|
| `element`/`color` 응답 형태 | 규격의 단일 문자열 대신 **배열 유지** | 값이 둘 이상인 에셋에서 데이터가 잘림, `color`와의 일관성, 입력은 규격대로 보내도 동작 | `app/schemas.py`의 `SearchHit` |
| `categories`/`styles` 별칭 | 폐기하지 않고 **네 경로 모두에서 수용** | 폐기하면 쓰던 클라이언트가 깨지지만, 받아주는 쪽은 순수 추가라 깨질 것이 없음 | `app/main.py`의 `LEGACY_FILTER_NAMES` |
| "모델 서버 연동"(3번 담당 항목) | **프로세스 내 모델 연결**로 구현 (물리적 별도 서버 아님) | 인수인계가 "시작 시 한 번 생성해 재사용"을 지시, 모델·어댑터·인덱스가 한 객체에 묶여 있음 | `app/main.py`의 `create_search_service` |
| Docker 모델 캐시 볼륨 | 현재 **비어 있는 채로 둠**(경로 불일치) | 검색 서비스가 캐시 경로를 하드코딩해 `FWS_*_CACHE`가 적용되지 않음 | `Dockerfile`의 `ENV`/`VOLUME` |

## 10. 남은 작업

- `element`/`color`는 메타데이터 규격에 단일 문자열(`"element": "fire"`)로
  적혀 있지만, **응답에서는 배열을 유지하기로 결정했습니다.** 한 에셋이 속성을
  여러 개 가질 수 있어(`["fire", "ice"]`) 규격을 그대로 따르면 두 번째 값부터
  응답에서 사라지기 때문입니다. 되돌리는 방법은 `app/schemas.py`의 `SearchHit`
  주석에 적어 두었습니다. 입력 필터는 문자열과 목록을 모두 받으므로 규격대로
  보내도 동작합니다.
- `elements` 태그 자체가 274개에만 채워져 있습니다. 태그 보강은 2번
  데이터·평가 담당의 작업입니다.
- `requirements.txt`와 `requirements-ai.txt`의 numpy 핀이 서로 다릅니다
  (1.26.4 / 2.4.4). 한쪽으로 통일하거나 `requirements-ai.txt`에서 numpy 핀을
  빼는 편이 안전합니다. 결정 전까지는 위 7절의 설치 순서를 지켜 주세요.
- `scripts/build_index.py`는 베이스라인 임베더로 `storage/indexes/weapons.faiss`를
  덮어쓰기 때문에 **실행 진입점을 주석 처리해 막아 두었습니다.** 인덱스를 다시
  만들 때는 `scripts/build_final_index.py`를 쓰세요.
- **Docker 컨테이너는 매 기동마다 모델을 다시 내려받습니다.** `FWS_MODEL_CACHE`와
  `FWS_TRANSLATION_CACHE`를 검색 서비스가 읽지 않고 `/app/.cache`에 하드코딩해
  두어, `VOLUME`으로 잡은 `/models/*`가 비어 있기 때문입니다. 동작에는 문제가
  없고 기동만 느립니다. 고치는 두 가지 방법을 `Dockerfile` 주석에 적어 두었으니,
  오프라인 환경에서 시연한다면 그 전에 (가) 안을 적용하세요.
- **모델 서버 분리는 선택 사항입니다.** 현재는 API 프로세스가 모델을 직접 올려
  연결하는 방식이고, 물리적으로 분리된 모델 서버가 필요해지면 바꿀 지점을
  `app/main.py`의 `create_search_service` 주석에 적어 두었습니다.
