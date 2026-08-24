"""현재 설정의 이미지 모델로 전체 에셋을 인코딩해 FAISS 인덱스를 만든다."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import faiss
import numpy as np
from PIL import Image

# 어느 작업 디렉터리에서 실행해도 프로젝트의 app 패키지를 import할 수 있게 한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.embeddings import OpenClipEmbedder
from app.repository import AssetRepository


def main():
    parser = argparse.ArgumentParser(description="판타지 무기 이미지 FAISS 인덱스 생성")
    parser.add_argument("--batch-size", type=int, default=None)
    args = parser.parse_args()
    settings = get_settings()
    batch_size = args.batch_size or settings.batch_size
    if batch_size <= 0:
        parser.error("--batch-size는 1 이상이어야 합니다")
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    # TEMPORARY BASELINE: 1번 담당자의 최종 모델이 들어오면 서버 설정과 이
    # 스크립트가 반드시 같은 embedder를 사용해야 한다. 서로 다른 모델로 만든
    # 질의 벡터와 이미지 인덱스는 차원이 같아도 의미적으로 호환되지 않는다.
    embedder = OpenClipEmbedder(
        settings.model_name,
        settings.pretrained,
        settings.device,
        settings.absolute(settings.model_cache),
    )

    vectors = []
    ids = []
    for offset in range(0, len(repository.assets), batch_size):
        batch = repository.assets[offset:offset + batch_size]
        images = []
        for asset in batch:
            # processed_file은 프로젝트 루트 기준 상대경로라는 데이터 계약을 따른다.
            path = settings.absolute(settings.image_root) / asset["processed_file"]
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        vectors.append(embedder.encode_images(images))
        ids.extend(asset["asset_id"] for asset in batch)
        print(f"encoded {min(offset + batch_size, len(repository.assets))}/{len(repository.assets)}", flush=True)

    matrix = np.concatenate(vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    index_path = settings.absolute(settings.index_path)
    ids_path = settings.absolute(settings.index_ids_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    ids_path.parent.mkdir(parents=True, exist_ok=True)

    # 완성되지 않은 파일을 서버가 읽지 않도록 임시 파일에 쓴 뒤 교체한다.
    # 두 파일을 완전히 동시에 교체할 수는 없으므로 서버 재시작 전 생성하는 것을 권장한다.
    with tempfile.NamedTemporaryFile(dir=index_path.parent, suffix=".faiss.tmp", delete=False) as handle:
        temp_index_path = Path(handle.name)
    with tempfile.NamedTemporaryFile(
        dir=ids_path.parent, suffix=".json.tmp", mode="w", encoding="utf-8", delete=False
    ) as handle:
        temp_ids_path = Path(handle.name)
        json.dump(ids, handle, ensure_ascii=False, indent=2)

    try:
        faiss.write_index(index, str(temp_index_path))
        os.replace(temp_index_path, index_path)
        os.replace(temp_ids_path, ids_path)
    finally:
        temp_index_path.unlink(missing_ok=True)
        temp_ids_path.unlink(missing_ok=True)
    print(f"saved {index.ntotal} vectors ({matrix.shape[1]} dimensions) to {index_path}")


# ======================================================================
# [실행 차단] 이 스크립트는 더 이상 쓰지 않는다.
#
# 위 main()은 베이스라인 OpenCLIP 임베더로 인코딩한 결과를
# storage/indexes/weapons.faiss 와 weapon_ids.json 에 덮어쓴다. 그런데 이
# 두 파일은 최종 어댑터 서비스(src/retrieval/search_service_adapter.py)가
# 읽는 바로 그 파일이다. 차원(512)과 개수(1391)가 같아 어댑터의 자체 검증은
# 통과하지만 벡터의 의미가 달라지고, service_manifest.json은 갱신되지 않아
# 다음 서버 기동이 sha256 불일치로 실패한다.
#
# 인덱스를 다시 만들 때는 scripts/build_final_index.py 를 사용할 것.
#
# 실수로 실행되는 것을 막기 위해 진입점만 주석 처리했다. 베이스라인 인덱스가
# 정말 필요하면 아래 주석을 풀기 전에 출력 경로(FWS_INDEX_PATH,
# FWS_INDEX_IDS_PATH)를 최종 산출물과 다른 곳으로 먼저 바꿔야 한다.
# ======================================================================
# if __name__ == "__main__":
#     main()
