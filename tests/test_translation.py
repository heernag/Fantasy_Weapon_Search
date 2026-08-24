"""[미사용] app/translation.py 테스트 — 대상 모듈과 함께 주석 처리했다.

검색 경로의 번역은 `src/retrieval/search_service.py`가 담당하며, 그 동작은
API 통합 테스트(한국어 질의 -> translated_text 확인)가 검증한다.
되살리려면 app/translation.py의 주석을 먼저 푼 뒤 아래 주석을 풀면 된다.
"""

# import pytest
#
#
# class FakeBackend:
#     def __init__(self, result="blue ice sword", error=None):
#         self.result = result
#         self.error = error
#         self.calls = []
#
#     def translate(self, text):
#         self.calls.append(text)
#         if self.error:
#             raise self.error
#         return self.result
#
#
# def test_english_bypasses_translation_backend():
#     from app.translation import KoreanEnglishTranslator
#
#     loads = []
#     translator = KoreanEnglishTranslator(backend_factory=lambda: loads.append(True))
#
#     search_text, translated = translator.translate_if_needed("blue sword")
#
#     assert search_text == "blue sword"
#     assert translated is None
#     assert loads == []
#
#
# def test_korean_loads_backend_once_and_returns_translation():
#     from app.translation import KoreanEnglishTranslator
#
#     backend = FakeBackend()
#     loads = []
#
#     def factory():
#         loads.append(True)
#         return backend
#
#     translator = KoreanEnglishTranslator(backend_factory=factory)
#
#     assert translator.translate_if_needed("파란 얼음 검") == ("blue ice sword", "blue ice sword")
#     assert translator.translate_if_needed("붉은 검") == ("blue ice sword", "blue ice sword")
#     assert loads == [True]
#     assert backend.calls == ["파란 얼음 검", "붉은 검"]
#
#
# def test_translation_failure_is_not_silently_ignored():
#     from app.translation import KoreanEnglishTranslator, TranslationError
#
#     backend = FakeBackend(error=RuntimeError("offline"))
#     translator = KoreanEnglishTranslator(backend_factory=lambda: backend)
#
#     with pytest.raises(TranslationError, match="한국어 번역에 실패했습니다"):
#         translator.translate_if_needed("파란 검")
