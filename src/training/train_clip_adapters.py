import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import open_clip
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[2]
MODEL_NAME = "ViT-B-16"
PRETRAINED = "laion2b_s34b_b88k"
EMBEDDING_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k"
TRAIN_PATH = ROOT / "data/splits/train.jsonl"
VALIDATION_PATH = ROOT / "data/splits/validation.jsonl"
OUTPUT_DIR = ROOT / "models/clip_adapter_vit_b16"
CACHE_DIR = ROOT / "outputs/clip_adapter_cache"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train lightweight residual adapters on frozen OpenCLIP embeddings."
    )
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--text-batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rebuild-text-cache", action="store_true")
    return parser.parse_args()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_image_embedding_table():
    embeddings = np.load(EMBEDDING_DIR / "image_embeddings.npy").astype(np.float32)
    with (EMBEDDING_DIR / "asset_ids.json").open("r", encoding="utf-8") as file:
        asset_ids = json.load(file)

    if len(asset_ids) != len(embeddings):
        raise ValueError("asset_ids and image_embeddings have different lengths")
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("Duplicate asset_id found in embedding table")

    return {asset_id: embeddings[index] for index, asset_id in enumerate(asset_ids)}


def select_image_embeddings(records, embedding_table):
    missing = [record["asset_id"] for record in records if record["asset_id"] not in embedding_table]
    if missing:
        raise KeyError(f"Missing image embeddings: {missing[:5]}")
    return np.stack([embedding_table[record["asset_id"]] for record in records]).astype(np.float32)


def encode_texts(records, split_name, batch_size, rebuild_cache, device):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{split_name}_caption_en_embeddings.npy"
    id_path = CACHE_DIR / f"{split_name}_asset_ids.json"
    expected_ids = [record["asset_id"] for record in records]

    if cache_path.exists() and id_path.exists() and not rebuild_cache:
        with id_path.open("r", encoding="utf-8") as file:
            cached_ids = json.load(file)
        cached = np.load(cache_path).astype(np.float32)
        if cached_ids == expected_ids and cached.shape == (len(records), 512):
            print(f"Using text cache: {cache_path}")
            return cached

    print(f"Generating {split_name} caption embeddings: {len(records)}")
    model, _, _ = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=device,
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model.eval()
    captions = [record["caption_en"] for record in records]
    batches = []

    for start in tqdm(range(0, len(captions), batch_size), desc=f"Text embeddings ({split_name})"):
        tokens = tokenizer(captions[start:start + batch_size]).to(device)
        with torch.inference_mode():
            features = model.encode_text(tokens)
            features = F.normalize(features, dim=-1)
        batches.append(features.cpu().numpy().astype(np.float32))

    embeddings = np.concatenate(batches, axis=0)
    np.save(cache_path, embeddings)
    with id_path.open("w", encoding="utf-8") as file:
        json.dump(expected_ids, file, ensure_ascii=False, indent=2)
    del model
    return embeddings


class ResidualAdapter(nn.Module):
    def __init__(self, dimension=512, hidden_dimension=128):
        super().__init__()
        self.down = nn.Linear(dimension, hidden_dimension)
        self.activation = nn.GELU()
        self.up = nn.Linear(hidden_dimension, dimension)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, features):
        residual = self.up(self.activation(self.down(features)))
        return F.normalize(features + residual, dim=-1)


class MultimodalAdapter(nn.Module):
    def __init__(self, dimension=512, hidden_dimension=128):
        super().__init__()
        self.image_adapter = ResidualAdapter(dimension, hidden_dimension)
        self.text_adapter = ResidualAdapter(dimension, hidden_dimension)

    def encode_image(self, features):
        return self.image_adapter(features)

    def encode_text(self, features):
        return self.text_adapter(features)


def symmetric_contrastive_loss(image_features, text_features, temperature):
    logits = image_features @ text_features.T / temperature
    labels = torch.arange(len(logits), device=logits.device)
    image_to_text = F.cross_entropy(logits, labels)
    text_to_image = F.cross_entropy(logits.T, labels)
    return (image_to_text + text_to_image) / 2


def recall_at_k(similarity, k):
    k = min(k, similarity.shape[1])
    top_indices = similarity.topk(k=k, dim=1).indices
    targets = torch.arange(similarity.shape[0], device=similarity.device).unsqueeze(1)
    return (top_indices == targets).any(dim=1).float().mean().item()


@torch.inference_mode()
def evaluate(model, image_features, text_features, temperature):
    model.eval()
    adapted_images = model.encode_image(image_features)
    adapted_texts = model.encode_text(text_features)
    similarity = adapted_images @ adapted_texts.T
    loss = symmetric_contrastive_loss(adapted_images, adapted_texts, temperature).item()

    text_to_image = similarity.T
    image_to_text = similarity
    metrics = {"loss": round(loss, 6)}
    for k in (1, 5, 10):
        metrics[f"text_to_image_recall@{k}"] = round(recall_at_k(text_to_image, k), 6)
        metrics[f"image_to_text_recall@{k}"] = round(recall_at_k(image_to_text, k), 6)
    metrics["mean_recall@1"] = round(
        (metrics["text_to_image_recall@1"] + metrics["image_to_text_recall@1"]) / 2,
        6,
    )
    metrics["mean_recall@5"] = round(
        (metrics["text_to_image_recall@5"] + metrics["image_to_text_recall@5"]) / 2,
        6,
    )
    return metrics


def is_better(metrics, best_metrics):
    if best_metrics is None:
        return True
    current_key = (metrics["mean_recall@5"], metrics["mean_recall@1"], -metrics["loss"])
    best_key = (best_metrics["mean_recall@5"], best_metrics["mean_recall@1"], -best_metrics["loss"])
    return current_key > best_key


def main():
    args = parse_args()
    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    start_time = time.time()

    train_records = load_jsonl(TRAIN_PATH)
    validation_records = load_jsonl(VALIDATION_PATH)
    if len(train_records) != 772 or len(validation_records) != 94:
        raise ValueError(
            f"Unexpected split sizes: train={len(train_records)}, validation={len(validation_records)}"
        )

    print(f"Device: {device}")
    print(f"Train: {len(train_records)}, validation: {len(validation_records)}")
    print("Test split is not used during training or model selection.")

    embedding_table = load_image_embedding_table()
    train_images = select_image_embeddings(train_records, embedding_table)
    validation_images = select_image_embeddings(validation_records, embedding_table)
    train_texts = encode_texts(
        train_records,
        "train",
        args.text_batch_size,
        args.rebuild_text_cache,
        device,
    )
    validation_texts = encode_texts(
        validation_records,
        "validation",
        args.text_batch_size,
        args.rebuild_text_cache,
        device,
    )

    train_dataset = TensorDataset(
        torch.from_numpy(train_images),
        torch.from_numpy(train_texts),
    )
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
    )
    validation_image_tensor = torch.from_numpy(validation_images).to(device)
    validation_text_tensor = torch.from_numpy(validation_texts).to(device)

    model = MultimodalAdapter(hidden_dimension=args.hidden_dim).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline_metrics = evaluate(
        model,
        validation_image_tensor,
        validation_text_tensor,
        args.temperature,
    )
    print(f"Baseline validation: {baseline_metrics}")

    history = []
    best_metrics = None
    best_epoch = 0
    epochs_without_improvement = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        seen = 0

        for image_batch, text_batch in train_loader:
            image_batch = image_batch.to(device)
            text_batch = text_batch.to(device)
            optimizer.zero_grad(set_to_none=True)
            adapted_images = model.encode_image(image_batch)
            adapted_texts = model.encode_text(text_batch)
            loss = symmetric_contrastive_loss(adapted_images, adapted_texts, args.temperature)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(image_batch)
            seen += len(image_batch)

        metrics = evaluate(
            model,
            validation_image_tensor,
            validation_text_tensor,
            args.temperature,
        )
        metrics["epoch"] = epoch
        metrics["train_loss"] = round(total_loss / seen, 6)
        history.append(metrics)
        print(
            f"Epoch {epoch:02d} | train_loss={metrics['train_loss']:.4f} "
            f"val_loss={metrics['loss']:.4f} "
            f"mean_R@1={metrics['mean_recall@1']:.4f} "
            f"mean_R@5={metrics['mean_recall@5']:.4f}"
        )

        if is_better(metrics, best_metrics):
            best_metrics = dict(metrics)
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "model_name": MODEL_NAME,
                    "pretrained": PRETRAINED,
                    "embedding_dimension": 512,
                    "hidden_dimension": args.hidden_dim,
                    "epoch": epoch,
                    "validation_metrics": best_metrics,
                },
                OUTPUT_DIR / "best_adapter.pt",
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print(f"Early stopping: no improvement for {args.patience} epochs")
                break

    elapsed = time.time() - start_time
    config = {
        "method": "frozen OpenCLIP encoders with trainable residual image/text adapters",
        "model_name": MODEL_NAME,
        "pretrained": PRETRAINED,
        "embedding_dimension": 512,
        "hidden_dimension": args.hidden_dim,
        "train_count": len(train_records),
        "validation_count": len(validation_records),
        "test_used": False,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "temperature": args.temperature,
        "seed": args.seed,
        "selection_rule": "highest validation mean Recall@5, then mean Recall@1, then lowest loss",
        "baseline_validation_metrics": baseline_metrics,
        "best_epoch": best_epoch,
        "best_validation_metrics": best_metrics,
        "elapsed_seconds": round(elapsed, 2),
    }
    with (OUTPUT_DIR / "config.json").open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
    with (OUTPUT_DIR / "training_history.json").open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)

    print("\nTraining complete")
    print(f"Best epoch: {best_epoch}")
    print(f"Best validation: {best_metrics}")
    print(f"Elapsed: {elapsed / 60:.1f} min")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
