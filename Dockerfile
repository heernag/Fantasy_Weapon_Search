FROM python:3.11-slim

# 모델 캐시 경로는 환경변수로 바꿀 수 없다. 검색 서비스
# (src/retrieval/search_service.py)가 OpenCLIP 캐시를 `self.root / ".cache/openclip"`,
# 번역 모델 캐시를 `self.root / ".cache/translation"`으로 하드코딩하고 있고, root는
# WORKDIR와 같은 /app이다. 그래서 FWS_MODEL_CACHE / FWS_TRANSLATION_CACHE를 여기서
# 지정해도 API는 읽지 않는다. 예전에는 그 두 변수와 /models/* 볼륨이 있었지만 실제
# 저장 위치와 어긋나 볼륨이 빈 채로 남았고, 컨테이너를 새로 만들 때마다 OpenCLIP과
# 번역 모델(합쳐 약 1.7GB)을 다시 내려받았다.
#
# 지금은 아래 VOLUME을 서비스가 실제로 쓰는 /app/.cache 하나로 맞춰 두었다.
# 서비스가 캐시 경로를 생성자 인자로 받도록 바뀌면(AI 담당 모듈 수정) 그때
# 환경변수 방식으로 되돌릴 수 있다.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FWS_DEVICE=cpu \
    FWS_PRELOAD_TRANSLATION_MODEL=true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# app/main.py가 src.retrieval의 최종 어댑터 서비스를 import하므로 함께 복사한다.
COPY src ./src
COPY data/metadata ./data/metadata
COPY data/processed ./data/processed
COPY storage/indexes ./storage/indexes
COPY models/clip_adapter_vit_b16 ./models/clip_adapter_vit_b16
COPY embeddings/ViT-B-16_laion2b_s34b_b88k_adapter ./embeddings/ViT-B-16_laion2b_s34b_b88k_adapter
RUN mkdir -p storage/logs .cache/openclip .cache/translation
# 검색 서비스가 모델을 받아 두는 위치. 이 볼륨을 붙여 두면 컨테이너를 다시 만들어도
# 1.7GB를 다시 내려받지 않는다. 위 주석의 하드코딩 경로와 반드시 같아야 한다.
VOLUME ["/app/.cache"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
