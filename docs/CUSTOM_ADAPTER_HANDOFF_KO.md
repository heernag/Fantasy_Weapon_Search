# 커스텀 멀티모달 어댑터 인수인계

## 최종 모델

- 베이스 모델: OpenCLIP `ViT-B-16` / `laion2b_s34b_b88k`
- 커스텀 학습: 이미지·텍스트 512차원 임베딩용 residual adapter
- 학습 데이터: train 772쌍
- 모델 선택: validation 94쌍, best epoch 8
- test 데이터는 학습 및 모델 선택에 사용하지 않음
- 결합검색 가중치: 이미지 0.4 / 텍스트 0.6

## API에서 사용할 서비스

기존 서비스 대신 아래 모듈에서 동일한 클래스 이름을 import한다.

```python
from src.retrieval.search_service_adapter import WeaponSearchService
```

생성 및 메서드 사용법, 필터, 응답 JSON 형식은 기존
`src/retrieval/search_service.py`와 동일하다.

```python
search_service = WeaponSearchService()

text_result = search_service.search_text("파란 얼음 검", top_k=10)
image_result = search_service.search_image(image_bytes, top_k=10)
multimodal_result = search_service.search_multimodal(
    image=image_bytes,
    text="금색으로 바꿔줘",
    top_k=10,
)
```

서비스는 API 시작 시 한 번만 생성하고 요청마다 재사용한다.

## 필수 파일

- `models/clip_adapter_vit_b16/best_adapter.pt`
- `embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/image_embeddings.npy`
- `embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/asset_ids.json`
- `embeddings/ViT-B-16_laion2b_s34b_b88k_adapter/model_info.json`

## 최종 test 성능

### 영어 40문항

- Recall@1: 0.300
- Recall@5: 0.500
- Recall@10: 0.550
- MRR: 0.392620
- mAP: 0.393314

### 한국어 번역 40문항

- Recall@1: 0.325
- Recall@5: 0.475
- Recall@10: 0.500
- MRR: 0.399616
- mAP: 0.400146

한국어는 `Helsinki-NLP/opus-mt-ko-en`으로 번역한 뒤 검색한다. 번역 모델의
색상 표현 오류는 남아 있으므로 향후 규칙 기반 색상 사전 또는 번역 모델 개선이
가능하다.
