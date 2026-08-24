"""이미지와 텍스트를 같은 벡터 공간으로 변환하는 임시 OpenCLIP 어댑터."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image


class OpenClipEmbedder:
    """공개 OpenCLIP 베이스라인의 로딩·전처리·정규화를 캡슐화한다.

    1번 최종 모델 연동 시 서비스 계층을 바꾸지 않고 이 클래스와 동일한
    `encode_texts`/`encode_images` 계약을 구현하는 어댑터로 교체할 예정이다.
    """

    def __init__(self, model_name: str, pretrained: str, device: str, cache_dir: Path):
        import open_clip

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.device = torch.device(device)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=self.device, cache_dir=str(cache_dir)
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.model.eval()

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        """IndexFlatIP 점수를 코사인 유사도로 쓰기 위해 L2 정규화한다."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return (vectors / np.clip(norms, 1e-12, None)).astype("float32")

    # ------------------------------------------------------------------
    # [미사용] 호출하는 곳이 없다. 이 클래스를 쓰는 유일한 코드인
    # scripts/build_index.py는 `encode_images`만 부른다. 텍스트 인코딩은
    # src/retrieval/search_service.py가 자체 구현으로 처리한다.
    # 삭제 대신 주석으로 남긴다(저장소가 git이 아니라 복구가 불가능하다).
    # ------------------------------------------------------------------
#     def encode_texts(self, texts: list[str]) -> np.ndarray:
#         """문장 배치를 float32 정규화 벡터로 변환한다."""
#         tokens = self.tokenizer(texts).to(self.device)
#         with torch.inference_mode():
#             vectors = self.model.encode_text(tokens).cpu().numpy()
#         return self._normalize(vectors)

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        """PIL 이미지 배치를 모델 고유 전처리 후 정규화 벡터로 변환한다."""
        batch = torch.stack([self.preprocess(image.convert("RGB")) for image in images]).to(self.device)
        with torch.inference_mode():
            vectors = self.model.encode_image(batch).cpu().numpy()
        return self._normalize(vectors)
