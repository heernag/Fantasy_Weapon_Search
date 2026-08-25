import json
from pathlib import Path

import open_clip
import torch
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "data/metadata/final_search_assets.jsonl"

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
DEVICE = "cpu"


def load_metadata():
    records = []

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def main():
    records = load_metadata()

    # sword, shield, axe를 각각 10장씩 선택
    selected = []

    for category in ["sword", "shield", "axe"]:
        category_records = [
            record for record in records
            if record["category"] == category
        ]
        selected.extend(category_records[:10])

    print(f"선택된 이미지: {len(selected)}장")

    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model.eval()

    image_tensors = []

    for record in selected:
        image_path = ROOT / record["processed_file"]

        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image_tensors.append(preprocess(image))

    image_batch = torch.stack(image_tensors)

    query = "a fantasy sword"
    text_tokens = tokenizer([query])

    with torch.inference_mode():
        image_embeddings = model.encode_image(image_batch)
        text_embedding = model.encode_text(text_tokens)

        image_embeddings /= image_embeddings.norm(dim=-1, keepdim=True)
        text_embedding /= text_embedding.norm(dim=-1, keepdim=True)

        similarities = image_embeddings @ text_embedding.T

    scores = similarities.squeeze(1)
    top_indices = scores.argsort(descending=True)[:5]

    print(f"\n검색어: {query}")
    print("검색 결과:")

    for rank, index in enumerate(top_indices.tolist(), start=1):
        record = selected[index]

        print(
            f"{rank}. "
            f"{record['asset_id']} | "
            f"{record['category']} | "
            f"{scores[index].item():.4f} | "
            f"{record['caption_en']}"
        )


if __name__ == "__main__":
    main()