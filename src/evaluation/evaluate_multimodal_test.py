import argparse
import json
from collections import defaultdict
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

import numpy as np
import open_clip
import torch
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[2]

EMBEDDING_DIR = (
    ROOT / "embeddings/ViT-B-32_laion2b_s34b_b79k"
)

QUERY_PATH = (
    ROOT
    / "data/evaluation/multimodal_queries.jsonl"
)

GROUND_TRUTH_PATH = (
    ROOT
    / "data/evaluation/multimodal_ground_truth.jsonl"
)

VALIDATION_PATH = ROOT / "data/splits/test.jsonl"
RESULT_PATH = ROOT / "results/multimodal_test_results.json"

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

WEIGHTS = [0.4]


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def normalize(vector):
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("벡터 norm이 0입니다.")

    return vector / norm


def average_precision(ranked_ids, relevant_ids):
    relevant = set(relevant_ids)

    if not relevant:
        return 0.0

    hit_count = 0
    precision_sum = 0.0

    for rank, asset_id in enumerate(ranked_ids, start=1):
        if asset_id in relevant:
            hit_count += 1
            precision_sum += hit_count / rank

    return precision_sum / len(relevant)


def calculate_metrics(query_results):
    count = len(query_results)

    if count == 0:
        return {}

    recall_1 = 0
    recall_5 = 0
    recall_10 = 0
    reciprocal_rank_sum = 0.0
    ap_sum = 0.0

    for result in query_results:
        ranked_ids = result["ranked_asset_ids"]
        relevant = set(result["relevant_asset_ids"])

        if relevant.intersection(ranked_ids[:1]):
            recall_1 += 1

        if relevant.intersection(ranked_ids[:5]):
            recall_5 += 1

        if relevant.intersection(ranked_ids[:10]):
            recall_10 += 1

        first_relevant_rank = None

        for rank, asset_id in enumerate(ranked_ids, start=1):
            if asset_id in relevant:
                first_relevant_rank = rank
                break

        if first_relevant_rank is not None:
            reciprocal_rank_sum += 1.0 / first_relevant_rank

        ap_sum += average_precision(
            ranked_ids,
            relevant,
        )

    return {
        "query_count": count,
        "Recall@1": round(recall_1 / count, 6),
        "Recall@5": round(recall_5 / count, 6),
        "Recall@10": round(recall_10 / count, 6),
        "MRR": round(reciprocal_rank_sum / count, 6),
        "mAP": round(ap_sum / count, 6),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--language",
        choices=["en", "ko", "all"],
        default="en",
        help="가중치 선택은 우선 en 사용 권장",
    )

    parser.add_argument(
    "--translate-ko",
    action="store_true",
    help="한국어 검색어를 영어로 번역한 후 평가",
    )

    args = parser.parse_args()

    queries = load_jsonl(QUERY_PATH)
    ground_truth_rows = load_jsonl(GROUND_TRUTH_PATH)
    validation_rows = load_jsonl(VALIDATION_PATH)

    ground_truth = {
        row["query_id"]: row["relevant_asset_ids"]
        for row in ground_truth_rows
    }

    if args.language != "all":
        queries = [
            query
            for query in queries
            if query["language"] == args.language
        ]

    image_embeddings = np.load(
        EMBEDDING_DIR / "image_embeddings.npy"
    )

    with (EMBEDDING_DIR / "asset_ids.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        all_asset_ids = json.load(file)

    if image_embeddings.shape[0] != len(all_asset_ids):
        raise ValueError(
            "임베딩 행 수와 asset_id 개수가 다릅니다."
        )

    asset_index = {
        asset_id: index
        for index, asset_id in enumerate(all_asset_ids)
    }

    validation_ids = [
        row["asset_id"]
        for row in validation_rows
    ]

    missing_ids = [
        asset_id
        for asset_id in validation_ids
        if asset_id not in asset_index
    ]

    if missing_ids:
        raise ValueError(
            f"임베딩에 없는 validation ID: {missing_ids[:5]}"
        )

    candidate_embeddings = np.stack(
        [
            image_embeddings[asset_index[asset_id]]
            for asset_id in validation_ids
        ]
    )

    model, _, _ = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE,
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model.eval()

    texts = [
        query["modification_text"]
        for query in queries
    ]

    translation_model_name = None

    if args.translate_ko:
        if args.language != "ko":
            raise ValueError(
                "--translate-ko는 --language ko와 함께 사용하세요."
            )

        translation_model_name = "Helsinki-NLP/opus-mt-ko-en"

        translation_tokenizer = AutoTokenizer.from_pretrained(
            translation_model_name
        )
        translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            translation_model_name
        ).to(DEVICE)
        translation_model.eval()

        translated_texts = []

        print("\n한국어 검색어 번역")

        for text in tqdm(texts, desc="한→영 번역"):
            inputs = translation_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
            ).to(DEVICE)

            with torch.inference_mode():
                generated = translation_model.generate(
                    **inputs,
                    max_new_tokens=64,
                )

            translated = translation_tokenizer.decode(
                generated[0],
                skip_special_tokens=True,
            )

            translated_texts.append(translated)

        for original, translated in zip(
            texts[:5],
            translated_texts[:5],
        ):
            print(f"{original} -> {translated}")

        texts = translated_texts

    text_batches = []
    batch_size = 32

    for start in tqdm(
        range(0, len(texts), batch_size),
        desc="텍스트 임베딩 생성",
    ):
        batch_texts = texts[start:start + batch_size]
        tokens = tokenizer(batch_texts).to(DEVICE)

        with torch.inference_mode():
            embeddings = model.encode_text(tokens)
            embeddings /= embeddings.norm(
                dim=-1,
                keepdim=True,
            )

        text_batches.append(
            embeddings.cpu().numpy().astype(np.float32)
        )

    text_embeddings = np.concatenate(
        text_batches,
        axis=0,
    )

    all_weight_results = []

    for image_weight in WEIGHTS:
        text_weight = 1.0 - image_weight
        query_results = []

        for query, text_vector in zip(
            queries,
            text_embeddings,
        ):
            query_image_id = query["query_image_id"]

            if query_image_id not in asset_index:
                raise ValueError(
                    f"기준 이미지 임베딩 없음: {query_image_id}"
                )

            image_vector = image_embeddings[
                asset_index[query_image_id]
            ]

            combined_vector = normalize(
                image_weight * image_vector
                + text_weight * text_vector
            )

            scores = candidate_embeddings @ combined_vector

            excluded = set(
                query.get("excluded_asset_ids", [])
            )

            ranked_indices = np.argsort(-scores)

            ranked_ids = [
                validation_ids[index]
                for index in ranked_indices
                if validation_ids[index] not in excluded
            ]

            relevant_ids = ground_truth[query["query_id"]]

            query_results.append(
                {
                    "query_id": query["query_id"],
                    "language": query["language"],
                    "query_type": query["query_type"],
                    "ranked_asset_ids": ranked_ids,
                    "relevant_asset_ids": relevant_ids,
                }
            )

        overall_metrics = calculate_metrics(query_results)

        by_type = {}

        grouped = defaultdict(list)

        for result in query_results:
            grouped[result["query_type"]].append(result)

        for query_type, group_results in grouped.items():
            by_type[query_type] = calculate_metrics(
                group_results
            )

        weight_result = {
            "image_weight": image_weight,
            "text_weight": text_weight,
            "overall": overall_metrics,
            "by_query_type": by_type,
        }

        all_weight_results.append(weight_result)

        print(
            f"\nimage={image_weight:.1f}, "
            f"text={text_weight:.1f}"
        )

        for name, value in overall_metrics.items():
            print(f"  {name}: {value}")

    best_result = max(
        all_weight_results,
        key=lambda result: (
            result["overall"]["MRR"],
            result["overall"]["Recall@1"],
            result["overall"]["mAP"],
        ),
    )

    output = {
        "dataset": "multimodal_test",
        "language": args.language,
        "model_name": MODEL_NAME,
        "pretrained": PRETRAINED,
        "translation_model": translation_model_name,
        "candidate_count": len(validation_ids),
        "weight_results": all_weight_results,
        "selected_weight": {
            "image_weight": best_result["image_weight"],
            "text_weight": best_result["text_weight"],
            "selection_rule": (
                "fixed at image 0.4 / text 0.6 from validation"
            ),
        },
    }

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n선택된 가중치")
    print(
        f"이미지: {best_result['image_weight']:.1f}, "
        f"텍스트: {best_result['text_weight']:.1f}"
    )
    print(f"결과 저장: {RESULT_PATH}")


if __name__ == "__main__":
    main()