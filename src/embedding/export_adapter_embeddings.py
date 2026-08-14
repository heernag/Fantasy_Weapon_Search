import json
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k"
CHECKPOINT_PATH = ROOT / "models/clip_adapter_vit_b16/best_adapter.pt"
OUTPUT_DIR = ROOT / "embeddings/ViT-B-16_laion2b_s34b_b88k_adapter"
BATCH_SIZE = 256


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


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    hidden_dimension = checkpoint["hidden_dimension"]
    model = MultimodalAdapter(
        dimension=checkpoint["embedding_dimension"],
        hidden_dimension=hidden_dimension,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    source_embeddings = np.load(SOURCE_DIR / "image_embeddings.npy").astype(np.float32)
    with (SOURCE_DIR / "asset_ids.json").open("r", encoding="utf-8") as file:
        asset_ids = json.load(file)

    if source_embeddings.shape != (len(asset_ids), 512):
        raise ValueError(
            f"Unexpected source shape: {source_embeddings.shape}, ids={len(asset_ids)}"
        )

    adapted_batches = []
    with torch.inference_mode():
        for start in range(0, len(source_embeddings), BATCH_SIZE):
            batch = torch.from_numpy(
                source_embeddings[start:start + BATCH_SIZE]
            ).to(device)
            adapted = model.image_adapter(batch)
            adapted_batches.append(adapted.cpu().numpy().astype(np.float32))

    adapted_embeddings = np.concatenate(adapted_batches, axis=0)
    norms = np.linalg.norm(adapted_embeddings, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-5):
        raise ValueError(f"Adapted vectors are not normalized: {norms.min()} ~ {norms.max()}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT_DIR / "image_embeddings.npy", adapted_embeddings)
    with (OUTPUT_DIR / "asset_ids.json").open("w", encoding="utf-8") as file:
        json.dump(asset_ids, file, ensure_ascii=False, indent=2)

    model_info = {
        "base_model_name": checkpoint["model_name"],
        "base_pretrained": checkpoint["pretrained"],
        "adapter_checkpoint": "models/clip_adapter_vit_b16/best_adapter.pt",
        "adapter_epoch": checkpoint["epoch"],
        "hidden_dimension": hidden_dimension,
        "embedding_dimension": 512,
        "normalized": True,
        "asset_count": len(asset_ids),
        "dtype": "float32",
        "source_embedding_dir": "embeddings/ViT-B-16_laion2b_s34b_b88k",
        "generated_at": datetime.now().isoformat(),
    }
    with (OUTPUT_DIR / "model_info.json").open("w", encoding="utf-8") as file:
        json.dump(model_info, file, ensure_ascii=False, indent=2)

    print("Adapter embedding export complete")
    print(f"shape: {adapted_embeddings.shape}")
    print(f"asset_id count: {len(asset_ids)}")
    print(f"vector norm: {norms.min():.6f} ~ {norms.max():.6f}")
    print(f"saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
