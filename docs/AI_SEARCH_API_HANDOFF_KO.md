# AI 검색 모듈 API 연동 안내

## 1. 최종 검색 설정

- 검색 모델: `ViT-B-16`
- 사전학습 가중치: `laion2b_s34b_b88k`
- 이미지 임베딩: `embeddings/ViT-B-16_laion2b_s34b_b88k/`
- 결합 검색 가중치: 이미지 `0.4`, 텍스트 `0.6`
- 한국어 입력: `Helsinki-NLP/opus-mt-ko-en`으로 영어 번역 후 검색
- 서비스 코드: `src/retrieval/search_service.py`

## 2. 중요: 모델은 한 번만 생성

`WeaponSearchService()`는 OpenCLIP 모델과 임베딩을 메모리에 올립니다.
요청 함수 안에서 매번 생성하지 말고 FastAPI 서버가 시작할 때 한 번 생성해
모든 요청에서 재사용해야 합니다.

```python
from src.retrieval.search_service import WeaponSearchService

search_service = WeaponSearchService()
```

CPU 환경에서는 최초 OpenCLIP 로딩과 최초 한국어 번역 모델 로딩에 시간이
걸릴 수 있습니다. 영어 검색만 실행하면 번역 모델은 로드하지 않습니다.

## 3. 텍스트 검색

```python
result = search_service.search_text(
    text="파란 얼음 검",
    top_k=10,
    filters={"category": "sword"},
)
```

## 4. 이미지 검색

파일 경로, 이미지 바이트 또는 `PIL.Image.Image`를 받을 수 있습니다.

```python
result = search_service.search_image(
    image=image_bytes,
    top_k=10,
    filters={"visual_style": "pixel_art"},
)
```

데이터셋 내부 파일 경로로 검색하면 기본적으로 동일한 원본 이미지는 결과에서
제외됩니다. 포함하려면 `include_self=True`를 전달합니다.

## 5. 이미지+텍스트 결합 검색

```python
result = search_service.search_multimodal(
    image=image_bytes,
    text="금색 판타지 검으로 바꿔줘",
    top_k=10,
    filters={"category": "sword"},
)
```

기본 가중치 `0.4/0.6`은 검증 세트에서 선택한 값이므로 API에서 임의로
변경하지 않는 것을 권장합니다.

## 6. 지원 필터

단일값 필터:

- `visual_style`
- `category`
- `subcategory`
- `primary_color`
- `grade`

목록 포함 필터:

- `colors`
- `materials`
- `elements`
- `shape_tags`

예시:

```python
filters = {
    "visual_style": "pixel_art",
    "category": "sword",
    "materials": ["steel"],
    "elements": ["ice"],
}
```

목록 필터에 여러 값을 전달하면 모든 값이 포함된 에셋만 검색 후보가 됩니다.

## 7. 반환 형식

모든 함수는 JSON 직렬화가 가능한 `dict`를 반환합니다.

```json
{
  "search_type": "multimodal",
  "query_text": "금색 판타지 검으로 바꿔줘",
  "translated_text": "Turn it into a golden fantasy sword.",
  "image_weight": 0.4,
  "text_weight": 0.6,
  "candidate_count": 499,
  "results": [
    {
      "asset_id": "asset_000930",
      "score": 0.699779,
      "combined_score": 0.699779,
      "image_score": 0.929635,
      "text_score": 0.31694,
      "visual_style": "pixel_art",
      "category": "sword",
      "subcategory": "falchion",
      "primary_color": "blue",
      "colors": ["blue", "gold", "bronze"],
      "materials": ["crystal", "bronze", "gold", "steel"],
      "elements": ["water"],
      "caption_en": "...",
      "caption_ko": "...",
      "image_path": "data/processed/pixel_art/asset_000930.png",
      "source_url": "https://...",
      "license": "CC0"
    }
  ]
}
```

- 텍스트/이미지 단독 검색의 `score`: 해당 단일 검색 유사도
- 결합 검색의 `score`, `combined_score`: 최종 결합 벡터 유사도
- `image_score`, `text_score`: 결합 검색 결과 분석용 개별 유사도

## 8. FastAPI 연결 예시

```python
from fastapi import FastAPI, File, Form, UploadFile

from src.retrieval.search_service import WeaponSearchService

app = FastAPI()
search_service = WeaponSearchService()


@app.get("/search/text")
def search_text(query: str, top_k: int = 10):
    return search_service.search_text(query, top_k=top_k)


@app.post("/search/image")
async def search_image(
    image: UploadFile = File(...),
    top_k: int = 10,
):
    image_bytes = await image.read()
    return search_service.search_image(image_bytes, top_k=top_k)


@app.post("/search/multimodal")
async def search_multimodal(
    image: UploadFile = File(...),
    text: str = Form(...),
    top_k: int = Form(10),
):
    image_bytes = await image.read()
    return search_service.search_multimodal(
        image=image_bytes,
        text=text,
        top_k=top_k,
    )
```

FastAPI 구현 위치와 라우터 구조는 백엔드 담당자의 기존 프로젝트 구조에 맞게
조정합니다.

## 9. 이미지 제공 방식

검색 결과의 `image_path`는 저장소 루트 기준 상대 경로입니다. 백엔드는 다음 중
하나를 선택해야 합니다.

1. `data/processed`를 정적 파일 경로로 마운트하고 URL로 변환
2. `asset_id` 기반 이미지 다운로드 API 제공

프론트엔드에 Windows 절대 경로를 반환하면 안 됩니다.

## 10. 예외 처리

다음 오류는 API에서 400 또는 404 응답으로 변환합니다.

- 빈 검색 문장: `ValueError`
- 지원하지 않는 필터: `ValueError`
- 검색 후보 없음: `ValueError`
- `top_k`가 1~100 범위를 벗어남: `ValueError`
- 이미지 파일 없음: `FileNotFoundError`

서버 시작 중 모델 또는 임베딩 파일을 불러오지 못한 오류는 500 응답보다
서버 시작 실패로 처리하는 것이 좋습니다.

## 11. 최종 평가 결과

ViT-B/16, 이미지 0.4 / 텍스트 0.6 기준 테스트 결과:

| 입력 | Recall@1 | Recall@5 | Recall@10 | MRR | mAP |
|---|---:|---:|---:|---:|---:|
| 영어 | 0.250 | 0.475 | 0.550 | 0.378418 | 0.378952 |
| 한국어→영어 번역 | 0.150 | 0.375 | 0.500 | 0.283699 | 0.283811 |

한국어 번역 문장이 어색해도 색상·재질·속성 핵심어가 보존되면 검색이
작동합니다. 한국어 성능의 주요 한계는 번역 품질입니다.
