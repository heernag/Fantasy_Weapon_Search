import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[2]

METADATA_PATH = ROOT / "data/metadata/final_search_assets.jsonl"
OUTPUT_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k"

MODEL_NAME = "ViT-B-16"
PRETRAINED = "laion2b_s34b_b88k"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 16


def load_metadata():
    records = []

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def metadata_sha256():
    return hashlib.sha256(METADATA_PATH.read_bytes()).hexdigest()


def main():
    start_time = time.time()
    records = load_metadata()

    print(f"메타데이터: {len(records)}개")
    print(f"사용 장치: {DEVICE}")
    print(f"배치 크기: {BATCH_SIZE}")

    if len(records) != 1391:
        raise ValueError(f"예상 데이터는 1391개지만 {len(records)}개입니다.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    model.eval()

    embedding_batches = []
    asset_ids = []

    for start in tqdm(
        range(0, len(records), BATCH_SIZE),
        desc="이미지 임베딩 생성",
    ):
        batch_records = records[start:start + BATCH_SIZE]
        image_tensors = []

        for record in batch_records:
            image_path = ROOT / record["processed_file"]

            if not image_path.exists():
                raise FileNotFoundError(
                    f"{record['asset_id']} 이미지 없음: {image_path}"
                )

            with Image.open(image_path) as image:
                image = image.convert("RGB")
                image_tensors.append(preprocess(image))

        image_batch = torch.stack(image_tensors).to(DEVICE)

        with torch.inference_mode():
            embeddings = model.encode_image(image_batch)
            embeddings = embeddings / embeddings.norm(
                dim=-1,
                keepdim=True,
            )

        embedding_batches.append(
            embeddings.cpu().numpy().astype(np.float32)
        )
        asset_ids.extend(
            record["asset_id"] for record in batch_records
        )

    image_embeddings = np.concatenate(embedding_batches, axis=0)

    if image_embeddings.shape != (len(records), 512):
        raise ValueError(
            f"예상 임베딩 크기와 다릅니다: {image_embeddings.shape}"
        )

    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("asset_id 중복이 발견됐습니다.")

    np.save(
        OUTPUT_DIR / "image_embeddings.npy",
        image_embeddings,
    )

    with (OUTPUT_DIR / "asset_ids.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            asset_ids,
            file,
            ensure_ascii=False,
            indent=2,
        )

    elapsed = time.time() - start_time

    model_info = {
        "model_name": MODEL_NAME,
        "pretrained": PRETRAINED,
        "device": DEVICE,
        "embedding_dimension": 512,
        "normalized": True,
        "asset_count": len(asset_ids),
        "batch_size": BATCH_SIZE,
        "dtype": "float32",
        "metadata_path": str(
            METADATA_PATH.relative_to(ROOT)
        ).replace("\\", "/"),
        "metadata_sha256": metadata_sha256(),
        "generated_at": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
    }

    with (OUTPUT_DIR / "model_info.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            model_info,
            file,
            ensure_ascii=False,
            indent=2,
        )

    norms = np.linalg.norm(image_embeddings, axis=1)

    print("\n생성 완료")
    print(f"임베딩 shape: {image_embeddings.shape}")
    print(f"asset_id 개수: {len(asset_ids)}")
    print(f"벡터 norm 범위: {norms.min():.6f} ~ {norms.max():.6f}")
    print(f"소요 시간: {elapsed / 60:.1f}분")
    print(f"저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()