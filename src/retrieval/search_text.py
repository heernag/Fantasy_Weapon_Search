import argparse
import json
from pathlib import Path

import numpy as np
import open_clip
import torch


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


def load_embeddings():
    embeddings = np.load(
        EMBEDDING_DIR / "image_embeddings.npy"
    )

    with (EMBEDDING_DIR / "asset_ids.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        asset_ids = json.load(file)

    if embeddings.shape[0] != len(asset_ids):
        raise ValueError(
            "임베딩 행 수와 asset_id 개수가 다릅니다."
        )

    return embeddings, asset_ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--query",
        required=True,
        help="영문 검색 문장",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--style",
        choices=[
            "pixel_art",
            "illustration",
            "rendered_icon",
        ],
    )
    parser.add_argument("--category")

    args = parser.parse_args()

    metadata = load_metadata()
    image_embeddings, asset_ids = load_embeddings()

    model, _, _ = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model.eval()

    text_tokens = tokenizer([args.query]).to(DEVICE)

    with torch.inference_mode():
        text_embedding = model.encode_text(text_tokens)
        text_embedding /= text_embedding.norm(
            dim=-1,
            keepdim=True,
        )

    text_vector = (
        text_embedding.cpu().numpy().astype(np.float32)[0]
    )

    similarities = image_embeddings @ text_vector

    candidate_indices = []

    for index, asset_id in enumerate(asset_ids):
        record = metadata[asset_id]

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

    if not candidate_indices:
        raise ValueError("검색 조건에 해당하는 이미지가 없습니다.")

    ranked_indices = sorted(
        candidate_indices,
        key=lambda index: similarities[index],
        reverse=True,
    )[:args.top_k]

    print(f"\n검색어: {args.query}")
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
