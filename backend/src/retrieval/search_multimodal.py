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


def normalize(vector):
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("벡터 norm이 0입니다.")

    return vector / norm


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--image", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--top-k", type=int, default=10)

    parser.add_argument(
        "--image-weight",
        type=float,
        default=0.5,
        help="이미지 가중치 0~1",
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

    if not 0 <= args.image_weight <= 1:
        raise ValueError("image-weight는 0~1이어야 합니다.")

    text_weight = 1.0 - args.image_weight

    metadata = load_metadata()

    image_embeddings = np.load(
        EMBEDDING_DIR / "image_embeddings.npy"
    )

    with (EMBEDDING_DIR / "asset_ids.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        asset_ids = json.load(file)

    query_image_path = Path(args.image)

    if not query_image_path.is_absolute():
        query_image_path = ROOT / query_image_path

    if not query_image_path.exists():
        raise FileNotFoundError(query_image_path)

    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model.eval()

    with Image.open(query_image_path) as image:
        image_tensor = (
            preprocess(image.convert("RGB"))
            .unsqueeze(0)
            .to(DEVICE)
        )

    text_tokens = tokenizer([args.text]).to(DEVICE)

    with torch.inference_mode():
        query_image_embedding = model.encode_image(
            image_tensor
        )
        query_text_embedding = model.encode_text(
            text_tokens
        )

        query_image_embedding /= query_image_embedding.norm(
            dim=-1,
            keepdim=True,
        )
        query_text_embedding /= query_text_embedding.norm(
            dim=-1,
            keepdim=True,
        )

    image_vector = (
        query_image_embedding.cpu().numpy()
        .astype(np.float32)[0]
    )
    text_vector = (
        query_text_embedding.cpu().numpy()
        .astype(np.float32)[0]
    )

    combined_vector = normalize(
        args.image_weight * image_vector
        + text_weight * text_vector
    )

    combined_scores = image_embeddings @ combined_vector
    image_scores = image_embeddings @ image_vector
    text_scores = image_embeddings @ text_vector

    input_resolved = query_image_path.resolve()
    candidate_indices = []

    for index, asset_id in enumerate(asset_ids):
        record = metadata[asset_id]
        candidate_path = (
            ROOT / record["processed_file"]
        ).resolve()

        # 기준 이미지 자체 제외
        if candidate_path == input_resolved:
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

    if not candidate_indices:
        raise ValueError("검색 후보가 없습니다.")

    ranked_indices = sorted(
        candidate_indices,
        key=lambda index: combined_scores[index],
        reverse=True,
    )[:args.top_k]

    print(f"\n기준 이미지: {query_image_path}")
    print(f"변경 문장: {args.text}")
    print(f"이미지 가중치: {args.image_weight:.2f}")
    print(f"텍스트 가중치: {text_weight:.2f}")
    print(f"검색 후보: {len(candidate_indices)}개")
    print(f"Top-{len(ranked_indices)} 결과\n")

    for rank, index in enumerate(ranked_indices, start=1):
        asset_id = asset_ids[index]
        record = metadata[asset_id]

        print(
            f"{rank}. {asset_id}\n"
            f"   combined: {combined_scores[index]:.4f}\n"
            f"   image: {image_scores[index]:.4f}\n"
            f"   text: {text_scores[index]:.4f}\n"
            f"   style: {record['visual_style']}\n"
            f"   category: {record['category']}\n"
            f"   subcategory: {record['subcategory']}\n"
            f"   primary_color: {record['primary_color']}\n"
            f"   colors: {record['colors']}\n"
            f"   caption: {record['caption_en']}\n"
            f"   image: {record['processed_file']}\n"
        )


if __name__ == "__main__":
    main()