import argparse
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import open_clip
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter"
CHECKPOINT_PATH = ROOT / "models/clip_adapter_vit_b16/best_adapter.pt"
QUERY_PATH = ROOT / "data/evaluation/multimodal_validation_queries.jsonl"
GROUND_TRUTH_PATH = ROOT / "data/evaluation/multimodal_validation_ground_truth.jsonl"
SPLIT_PATH = ROOT / "data/splits/validation.jsonl"
MODEL_NAME = "ViT-B-16"
PRETRAINED = "laion2b_s34b_b88k"
# 0.0은 텍스트 전용, 1.0은 이미지 전용이며 그 사이 값은 멀티모달 조합이다.
# 세 검색 모드를 실제 같은 검증 세트에서 비교할 수 있게 양 끝값을 모두 포함한다.
WEIGHTS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def update_evaluation_history(metrics):
    """하루에 한 번의 최신 검증 결과만 추이 파일에 보관한다."""
    history_path = ROOT / "results/evaluation_history.jsonl"
    today = date.today().isoformat()
    current = {
        "date": today,
        "dataset": "multimodal_validation",
        "recall_at_10": metrics["Recall@10"],
        "mrr": metrics["MRR"],
        "ndcg": metrics["nDCG@10"],
    }
    existing = load_jsonl(history_path) if history_path.exists() else []
    # 같은 날짜·데이터셋은 재실행 결과로 대체한다. 이렇게 해야 그래프의 X축이
    # 날짜별 1개 값이라는 계약을 지키고, 재실행이 중복 막대를 만들지 않는다.
    retained = [
        row for row in existing
        if not (row.get("date") == today and row.get("dataset") == current["dataset"])
    ]
    retained.append(current)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as file:
        for row in retained:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(vector):
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("Cannot normalize a zero vector")
    return vector / norm


def average_precision(ranked_ids, relevant_ids):
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for rank, asset_id in enumerate(ranked_ids, start=1):
        if asset_id in relevant:
            hits += 1
            total += hits / rank
    return total / len(relevant)


def calculate_metrics(results):
    count = len(results)
    recalls = {1: 0, 5: 0, 10: 0}
    reciprocal_rank_sum = 0.0
    ap_sum = 0.0
    ndcg_sum = 0.0
    for result in results:
        ranked = result["ranked_asset_ids"]
        relevant = set(result["relevant_asset_ids"])
        for k in recalls:
            recalls[k] += int(bool(relevant.intersection(ranked[:k])))
        first_rank = next(
            (rank for rank, asset_id in enumerate(ranked, start=1) if asset_id in relevant),
            None,
        )
        if first_rank is not None:
            reciprocal_rank_sum += 1.0 / first_rank
        ap_sum += average_precision(ranked, relevant)
        dcg = sum(1 / np.log2(rank + 1) for rank, asset_id in enumerate(ranked[:10], start=1) if asset_id in relevant)
        ideal = sum(1 / np.log2(rank + 1) for rank in range(1, min(len(relevant), 10) + 1))
        ndcg_sum += dcg / ideal if ideal else 0.0
    return {
        "query_count": count,
        "Recall@1": round(recalls[1] / count, 6),
        "Recall@5": round(recalls[5] / count, 6),
        "Recall@10": round(recalls[10] / count, 6),
        "MRR": round(reciprocal_rank_sum / count, 6),
        "mAP": round(ap_sum / count, 6),
        "nDCG@10": round(ndcg_sum / count, 6),
    }


class ResidualAdapter(nn.Module):
    def __init__(self, dimension=512, hidden_dimension=128):
        super().__init__()
        self.down = nn.Linear(dimension, hidden_dimension)
        self.activation = nn.GELU()
        self.up = nn.Linear(hidden_dimension, dimension)

    def forward(self, features):
        return F.normalize(
            features + self.up(self.activation(self.down(features))),
            dim=-1,
        )


class MultimodalAdapter(nn.Module):
    def __init__(self, dimension=512, hidden_dimension=128):
        super().__init__()
        self.image_adapter = ResidualAdapter(dimension, hidden_dimension)
        self.text_adapter = ResidualAdapter(dimension, hidden_dimension)


def translate_korean(texts, device):
    model_name = "Helsinki-NLP/opus-mt-ko-en"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)
    model.eval()
    translated = []
    for text in tqdm(texts, desc="Korean to English"):
        inputs = tokenizer(text, return_tensors="pt", truncation=True).to(device)
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=64)
        translated.append(tokenizer.decode(generated[0], skip_special_tokens=True))
    return translated, model_name


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
    texts = [query["modification_text"] for query in queries]
    translation_model = None
    if args.translate_ko:
        texts, translation_model = translate_korean(texts, device)
        for original, translated in zip(
            [query["modification_text"] for query in queries[:5]], texts[:5]
        ):
            print(f"{original} -> {translated}")

    batches = []
    for start in tqdm(range(0, len(texts), 32), desc="Adapted text embeddings"):
        tokens = tokenizer(texts[start:start + 32]).to(device)
        with torch.inference_mode():
            base = F.normalize(clip_model.encode_text(tokens), dim=-1)
            adapted = adapter.text_adapter(base)
        batches.append(adapted.cpu().numpy().astype(np.float32))
    text_embeddings = np.concatenate(batches, axis=0)

    weight_results = []
    for image_weight in WEIGHTS:
        text_weight = 1.0 - image_weight
        query_results = []
        for query, text_vector in zip(queries, text_embeddings):
            started = time.perf_counter()
            image_vector = image_embeddings[asset_index[query["query_image_id"]]]
            combined = normalize(image_weight * image_vector + text_weight * text_vector)
            scores = candidate_embeddings @ combined
            excluded = set(query.get("excluded_asset_ids", []))
            ranked_ids = [
                candidate_ids[index]
                for index in np.argsort(-scores)
                if candidate_ids[index] not in excluded
            ]
            relevant_ids = ground_truth[query["query_id"]]
            first_rank = next((rank for rank, asset_id in enumerate(ranked_ids, start=1) if asset_id in set(relevant_ids)), None)
            query_results.append(
                {
                    "query_id": query["query_id"],
                    "query_text": query["modification_text"],
                    "language": query["language"],
                    "query_type": query["query_type"],
                    "ranked_asset_ids": ranked_ids,
                    "top_results": [{"asset_id": candidate_ids[index], "score": round(float(scores[index]), 6)} for index in np.argsort(-scores)[:10] if candidate_ids[index] not in excluded],
                    "relevant_asset_ids": relevant_ids,
                    "first_relevant_rank": first_rank,
                    "success": first_rank is not None,
                    "zero_result": not ranked_ids,
                    "search_elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )

        grouped = defaultdict(list)
        for result in query_results:
            grouped[result["query_type"]].append(result)
        metrics = calculate_metrics(query_results)
        result = {
            "image_weight": image_weight,
            "text_weight": text_weight,
            "overall": metrics,
            "by_query_type": {
                query_type: calculate_metrics(rows)
                for query_type, rows in grouped.items()
            },
            "query_logs": query_results,
        }
        weight_results.append(result)
        print(f"\nimage={image_weight:.1f}, text={text_weight:.1f}")
        for name, value in metrics.items():
            print(f"  {name}: {value}")

    best = max(
        weight_results,
        key=lambda row: (
            row["overall"]["MRR"],
            row["overall"]["Recall@1"],
            row["overall"]["mAP"],
        ),
    )
    suffix = "ko_translated" if args.translate_ko else args.language
    result_path = ROOT / f"results/multimodal_validation_results_adapter_{suffix}.json"
    output = {
        "dataset": "multimodal_validation",
        "language": args.language,
        "model_name": MODEL_NAME,
        "pretrained": PRETRAINED,
        "adapter_checkpoint": "models/clip_adapter_vit_b16/best_adapter.pt",
        "translation_model": translation_model,
        "candidate_count": len(candidate_ids),
        "weight_results": weight_results,
        "selected_weight": {
            "image_weight": best["image_weight"],
            "text_weight": best["text_weight"],
            "selection_rule": "highest MRR, then Recall@1, then mAP",
        },
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    log_path = result_path.with_name(result_path.stem + "_query_logs.jsonl")
    selected = next(row for row in weight_results if row["image_weight"] == best["image_weight"])
    with log_path.open("w", encoding="utf-8") as file:
        for row in selected["query_logs"]:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    update_evaluation_history(selected["overall"])
    print("\nSelected weight")
    print(f"image: {best['image_weight']:.1f}, text: {best['text_weight']:.1f}")
    print(f"saved to: {result_path}")


if __name__ == "__main__":
    main()
