import argparse
import json
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "data/metadata/final_search_assets.jsonl"
EMBEDDING_DIR = (
    ROOT / "embeddings/ViT-B-32_laion2b_s34b_b79k"
)

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_metadata():
    records = []

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return {record["asset_id"]: record for record in records}


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True,
        help="검색에 사용할 이미지 경로",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--style",
        choices=[
            "pixel_art",
            "illustration",
            "rendered_icon",
        ],
    )
    parser.add_argument("--category")
    parser.add_argument(
        "--include-self",
        action="store_true",
        help="기준 이미지 자체도 결과에 포함",
    )

    args = parser.parse_args()

    metadata = load_metadata()

    image_embeddings = np.load(
        EMBEDDING_DIR / "image_embeddings.npy"
    )

    with (EMBEDDING_DIR / "asset_ids.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        asset_ids = json.load(file)

    if image_embeddings.shape[0] != len(asset_ids):
        raise ValueError("임베딩과 asset_id 개수가 다릅니다.")

    input_path = Path(args.image)

    if not input_path.is_absolute():
        input_path = ROOT / input_path

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    model.eval()

    with Image.open(input_path) as image:
        image_tensor = (
            preprocess(image.convert("RGB"))
            .unsqueeze(0)
            .to(DEVICE)
        )

    with torch.inference_mode():
        query_embedding = model.encode_image(image_tensor)
        query_embedding /= query_embedding.norm(
            dim=-1,
            keepdim=True,
        )

    query_vector = (
        query_embedding.cpu().numpy().astype(np.float32)[0]
    )

    similarities = image_embeddings @ query_vector

    input_resolved = input_path.resolve()
    candidate_indices = []

    for index, asset_id in enumerate(asset_ids):
        record = metadata[asset_id]
        candidate_path = (
            ROOT / record["processed_file"]
        ).resolve()

        if (
            not args.include_self
            and candidate_path == input_resolved
        ):
            continue

        if (
            args.style
            and record["visual_style"] != args.style
        ):
            continue

        if (
            args.category
            and record["category"] != args.category
        ):
            continue

        candidate_indices.append(index)

    ranked_indices = sorted(
        candidate_indices,
        key=lambda index: similarities[index],
        reverse=True,
    )[:args.top_k]

    print(f"\n기준 이미지: {input_path}")
    print(f"검색 후보: {len(candidate_indices)}개")
    print(f"Top-{len(ranked_indices)} 결과\n")

    for rank, index in enumerate(ranked_indices, start=1):
        asset_id = asset_ids[index]
        record = metadata[asset_id]

        print(
            f"{rank}. {asset_id}\n"
            f"   score: {similarities[index]:.4f}\n"
            f"   style: {record['visual_style']}\n"
            f"   category: {record['category']}\n"
            f"   subcategory: {record['subcategory']}\n"
            f"   caption: {record['caption_en']}\n"
            f"   image: {record['processed_file']}\n"
        )


if __name__ == "__main__":
    main()