"""[미사용] API 계층의 한국어 번역 구현 — 현재 아무도 import하지 않는다.

운영 번역은 `src/retrieval/search_service.py`가 자체적으로 수행한다. 같은 모델
(`Helsinki-NLP/opus-mt-ko-en`)을 쓰고, 한글 감지 후 번역해 검색하는 흐름도 같다.
이 모듈은 그 구현이 들어오기 전에 API 쪽에서 준비했던 것으로, 지금은 검색 경로에
전혀 관여하지 않는다. 테스트(tests/test_translation.py)만 이 파일을 붙들고 있었다.

저장소가 git으로 관리되지 않아 삭제하면 되살릴 수 없으므로 아래에 전문을 주석으로
남긴다. API 계층에서 번역을 직접 다뤄야 할 일이 생기면 주석을 풀고
`tests/test_translation.py`도 함께 되살리면 된다.
"""

# """한글 질의만 최종 검색 계약의 영어 번역 모델로 변환한다."""
#
# import re
# from pathlib import Path
#
# import torch
#
#
# HANGUL_PATTERN = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]")
#
#
# class TranslationError(RuntimeError):
#     pass
#
#
# class TransformersTranslationBackend:
#     def __init__(self, model_name: str, device: str, cache_dir: Path):
#         from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
#
#         self.device = torch.device(device)
#         self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
#         self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(cache_dir)).to(self.device)
#         self.model.eval()
#
#     def translate(self, text: str) -> str:
#         inputs = self.tokenizer(text, return_tensors="pt", truncation=True).to(self.device)
#         with torch.inference_mode():
#             generated = self.model.generate(**inputs, max_new_tokens=64)
#         return self.tokenizer.decode(generated[0], skip_special_tokens=True).strip()
#
#
# class KoreanEnglishTranslator:
#     def __init__(
#         self,
#         model_name: str = "Helsinki-NLP/opus-mt-ko-en",
#         device: str = "cpu",
#         cache_dir: Path = Path(".cache/translation"),
#         *,
#         backend_factory=None,
#     ):
#         self.model_name = model_name
#         self.device = device
#         self.cache_dir = cache_dir
#         self.backend_factory = backend_factory or (
#             lambda: TransformersTranslationBackend(self.model_name, self.device, self.cache_dir)
#         )
#         self._backend = None
#
#     def translate_if_needed(self, text: str) -> tuple[str, str | None]:
#         if not HANGUL_PATTERN.search(text):
#             return text, None
#         try:
#             if self._backend is None:
#                 self._backend = self.backend_factory()
#             translated = self._backend.translate(text)
#         except Exception as exc:
#             raise TranslationError("한국어 번역에 실패했습니다") from exc
#         if not translated:
#             raise TranslationError("한국어 번역에 실패했습니다: 빈 번역 결과")
#         return translated, translated
