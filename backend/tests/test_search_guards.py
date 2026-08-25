import numpy as np
import pytest
from pydantic import ValidationError

from app.schemas import TextSearchRequest
from src.retrieval.search_service_adapter import WeaponSearchService


def test_text_query_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        TextSearchRequest(query="   ")


def test_multimodal_combine_rejects_different_dimensions():
    image_vector = np.ones((1, 512), dtype="float32")
    text_vector = np.ones((1, 768), dtype="float32")
    with pytest.raises(ValueError, match="shape"):
        WeaponSearchService._combine_vectors(image_vector, text_vector, 0.5)


def test_multimodal_combine_rejects_zero_vector():
    image_vector = np.ones((1, 2), dtype="float32")
    text_vector = -np.ones((1, 2), dtype="float32")
    with pytest.raises(ValueError, match="zero vector"):
        WeaponSearchService._combine_vectors(image_vector, text_vector, 0.5)
