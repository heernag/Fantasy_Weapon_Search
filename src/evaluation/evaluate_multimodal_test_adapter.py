import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import open_clip
import torch
import torch.nn.functional as F
from tqdm import tqdm

from evaluate_multimodal_validation_adapter import (
    MultimodalAdapter,
    calculate_metrics,
    load_jsonl,
    normalize,
    translate_korean,
)


ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter"
CHECKPOINT_PATH = ROOT / "models/clip_adapter_vit_b16/best_adapter.pt"
QUERY_PATH = ROOT / "data/evaluation/multimodal_queries.jsonl"
GROUND_TRUTH_PATH = ROOT / "data/evaluation/multimodal_ground_truth.jsonl"
SPLIT_PATH = ROOT / "data/splits/test.jsonl"
MODEL_NAME = "ViT-B-16"
PRETRAINED = "laion2b_s34b_b88k"
IMAGE_WEIGHT = 0.4
TEXT_WEIGHT = 0.6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["en", "ko"], default="en")
    parser.add_argument("--translate-ko", action="store_true")
    args = parser.parse_args()
    if args.translate_ko and args.language != "ko":
        raise ValueError("--translate-ko requires --language ko")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    queries = [
        row for row in load_jsonl(QUERY_PATH)
        if row["language"] == args.language
    ]
    ground_truth = {
        row["query_id"]: row["relevant_asset_ids"]
        for row in load_jsonl(GROUND_TRUTH_PATH)
    }
    candidate_ids = [row["asset_id"] for row in load_jsonl(SPLIT_PATH)]

    image_embeddings = np.load(EMBEDDING_DIR / "image_embeddings.npy").astype(np.float32)
    with (EMBEDDING_DIR / "asset_ids.json").open("r", encoding="utf-8") as file:
        all_asset_ids = json.load(file)
    asset_index = {asset_id: index for index, asset_id in enumerate(all_asset_ids)}
    candidate_embeddings = np.stack(
        [image_embeddings[asset_index[asset_id]] for asset_id in candidate_ids]
    )

    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    adapter = MultimodalAdapter(
        checkpoint["embedding_dimension"], checkpoint["hidden_dimension"]
    ).to(device)
    adapter.load_state_dict(checkpoint["model_state_dict"])
    adapter.eval()

    clip_model, _, _ = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED, device=device
    )
    clip_model.eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)

    original_texts = [query["modification_text"] for query in queries]
    texts = original_texts
    translation_model = None
    if args.translate_ko:
        texts, translation_model = translate_korean(texts, device)
        for original, translated in zip(original_texts[:5], texts[:5]):
            print(f"{original} -> {translated}")

    batches = []
    for start in tqdm(range(0, len(texts), 32), desc="Adapted text embeddings"):
        tokens = tokenizer(texts[start:start + 32]).to(device)
        with torch.inference_mode():
            base = F.normalize(clip_model.encode_text(tokens), dim=-1)
            adapted = adapter.text_adapter(base)
        batches.append(adapted.cpu().numpy().astype(np.float32))
    text_embeddings = np.concatenate(batches, axis=0)

    query_results = []
    for query, text_vector in zip(queries, text_embeddings):
        image_vector = image_embeddings[asset_index[query["query_image_id"]]]
        combined = normalize(
            IMAGE_WEIGHT * image_vector + TEXT_WEIGHT * text_vector
        )
        scores = candidate_embeddings @ combined
        excluded = set(query.get("excluded_asset_ids", []))
        ranked_ids = [
            candidate_ids[index]
            for index in np.argsort(-scores)
            if candidate_ids[index] not in excluded
        ]
        query_results.append(
            {
                "query_id": query["query_id"],
                "query_type": query["query_type"],
                "ranked_asset_ids": ranked_ids,
                "relevant_asset_ids": ground_truth[query["query_id"]],
            }
        )

    grouped = defaultdict(list)
    for result in query_results:
        grouped[result["query_type"]].append(result)
    overall = calculate_metrics(query_results)
    by_type = {
        query_type: calculate_metrics(rows)
        for query_type, rows in grouped.items()
    }

    suffix = "ko_translated" if args.translate_ko else args.language
    result_path = ROOT / f"results/multimodal_test_results_adapter_{suffix}.json"
    output = {
        "dataset": "multimodal_test",
        "language": args.language,
        "model_name": MODEL_NAME,
        "pretrained": PRETRAINED,
        "adapter_checkpoint": "models/clip_adapter_vit_b16/best_adapter.pt",
        "translation_model": translation_model,
        "candidate_count": len(candidate_ids),
        "fixed_weight": {
            "image_weight": IMAGE_WEIGHT,
            "text_weight": TEXT_WEIGHT,
            "selected_on": "multimodal validation set",
        },
        "overall": overall,
        "by_query_type": by_type,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"\nimage={IMAGE_WEIGHT:.1f}, text={TEXT_WEIGHT:.1f}")
    for name, value in overall.items():
        print(f"  {name}: {value}")
    print(f"saved to: {result_path}")


if __name__ == "__main__":
    main()
