"""API 요청·응답 계약과 경계값 검증을 정의한다."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_IMAGE_WEIGHT = 0.4
DEFAULT_TEXT_WEIGHT = 0.6


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual_style: str | None = None
    category: str | None = None
    subcategory: str | None = None
    primary_color: str | None = None
    grade: str | None = None
    colors: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    shape_tags: list[str] = Field(default_factory=list)

    # 원래 팀 디자인 문서의 공식 필드명이다. 내부 검색 계약은 복수형 목록을
    # 유지하므로 API 경계에서 colors/elements로 합친 뒤 그 결과만 검색과 로그에 쓴다.
    color: str | list[str] | None = Field(default=None, exclude=True)
    element: str | list[str] | None = Field(default=None, exclude=True)

    # 초기 설계 문서의 메타데이터 규격에 있는 공식 속성이다. `/filters`도 두 이름을 그대로
    # 노출하며, 값 표기는 repository.canonicalize가 메타데이터 쪽에 맞춘다.
    style: str | None = Field(default=None, exclude=True)
    handedness: str | None = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_names(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for legacy, canonical in (("categories", "category"), ("styles", "style")):
            if legacy not in data:
                continue
            values = data.pop(legacy)
            if values in (None, [], ""):
                continue
            if not isinstance(values, list) or len(values) != 1:
                raise ValueError(f"{legacy} 호환 입력은 값 하나만 허용합니다")
            if canonical in data and data[canonical] != values[0]:
                raise ValueError(f"{legacy}와 {canonical} 값이 충돌합니다")
            data[canonical] = values[0]
        if isinstance(data.get("handedness"), list):
            values = data["handedness"]
            if not values:
                data.pop("handedness")
            elif len(values) == 1:
                data["handedness"] = values[0]
            else:
                raise ValueError("handedness 호환 입력은 값 하나만 허용합니다")
        return data

    @field_validator(
        "visual_style", "category", "subcategory", "primary_color", "grade",
        "style", "handedness",
    )
    @classmethod
    def scalar_filters_must_not_be_blank(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("필터 값은 비어 있을 수 없습니다")
        return normalized

    @field_validator("colors", "elements", "materials", "shape_tags")
    @classmethod
    def list_filters_must_not_contain_blanks(cls, values: list[str]):
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("필터 값은 비어 있을 수 없습니다")
        return normalized

    @field_validator("color", "element")
    @classmethod
    def original_list_filters_must_not_contain_blanks(cls, value: str | list[str] | None):
        if value is None:
            return None
        values = [value] if isinstance(value, str) else value
        normalized = [item.strip() for item in values]
        if not normalized or any(not item for item in normalized):
            raise ValueError("필터 값이 비어 있을 수 없습니다")
        return normalized[0] if isinstance(value, str) else normalized

    @staticmethod
    def _as_list(value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        return [value] if isinstance(value, str) else list(value)

    @staticmethod
    def _normalized_set(values: list[str]) -> set[str]:
        return {value.strip().lower() for value in values}

    @model_validator(mode="after")
    def original_and_extended_names_must_not_conflict(self):
        pairs = (
            ("color", self._as_list(self.color), "colors", self.colors),
            ("element", self._as_list(self.element), "elements", self.elements),
        )
        for original_name, original_values, extended_name, extended_values in pairs:
            if (
                original_values
                and extended_values
                and self._normalized_set(original_values) != self._normalized_set(extended_values)
            ):
                raise ValueError(f"{original_name}와 {extended_name} 값이 충돌합니다")
        return self

    def canonical_colors(self) -> list[str]:
        return list(self.colors) if self.colors else self._as_list(self.color)

    def canonical_elements(self) -> list[str]:
        return list(self.elements) if self.elements else self._as_list(self.element)


# 검색 서비스(`src/retrieval/search_service.py`의 `_validate_top_k`)가 한 번에
# 매기는 순위 상한이다. API 쪽 경계값은 전부 이 상수에서 나오고, 서비스와 값이
# 어긋나지 않는지는 tests/test_api_contract.py가 확인한다.
MAX_RANKED_RESULTS = 100


def validate_page(top_k: int, offset: int) -> None:
    """페이지는 서비스가 매기는 순위 창 안에 있어야 한다."""
    if offset + top_k > MAX_RANKED_RESULTS:
        raise ValueError(
            f"offset과 top_k의 합은 {MAX_RANKED_RESULTS} 이하여야 합니다: "
            f"{offset} + {top_k}"
        )


class TextSearchRequest(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=500)]
    top_k: Annotated[int, Field(ge=1, le=MAX_RANKED_RESULTS)] = 10
    offset: Annotated[int, Field(ge=0, le=MAX_RANKED_RESULTS - 1)] = 0
    filters: SearchFilters = Field(default_factory=SearchFilters)

    @model_validator(mode="after")
    def page_must_fit_the_ranked_window(self):
        validate_page(self.top_k, self.offset)
        return self

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query가 비어 있습니다")
        return value


class SearchHit(BaseModel):
    asset_id: str
    score: float
    image_path: str
    image_url: str
    metadata: dict
    result_text: str

    # [의도적 결정] 초기 설계 문서의 메타데이터 규격은 `"element": "fire"`처럼 단일
    # 문자열로 적혀 있다. 규격을 알고도 따르지 않기로 정한 것이므로, 규격과
    # 코드가 달라 보인다는 이유만으로 되돌리지 말 것.
    #
    # 판단 근거 세 가지 —
    # 1. 실제 데이터에 값이 둘 이상인 에셋이 있다(`elements: ["fire", "ice"]`).
    #    단일 문자열로 바꾸면 두 번째 값부터 응답에서 사라진다. 규격을 따르는
    #    대가가 데이터 손실이라면 규격 쪽이 현실을 덜 반영한 것으로 본다.
    # 2. 같은 규격에서 `color`는 이미 배열(`["gold", "red"]`)이다. `element`만
    #    스칼라로 두면 같은 성격의 두 속성이 서로 다른 모양이 된다.
    # 3. 규격이 실제로 필요한 곳은 입력이다. 입력 필터는 문자열과 목록을 모두
    #    받으므로 프론트엔드가 규격대로 보내도 그대로 동작한다. 즉 규격을
    #    따르지 않아 생기는 불편이 없다.
    #
    # 규격 쪽으로 되돌리려면 이 두 필드를 `str | None`로 바꾸고,
    # app/official_search.py의 `_enrich_hit`에서 목록의 첫 값만 넣도록 고친 뒤
    # tests/test_api_contract.py의
    # `test_multi_valued_attributes_stay_lists_in_the_response`와
    # tests/test_official_service_wiring.py의
    # `hit["element"] == hit["elements"]` 단언을 함께 수정한다.
    # 값이 둘 이상인 에셋은 이 배열 형태에서만 온전히 실린다.
    color: list[str] = Field(default_factory=list)
    element: list[str] = Field(default_factory=list)
    source: str | None = None
    combined_score: float | None = None
    image_score: float | None = None
    text_score: float | None = None
    visual_style: str | None = None
    category: str | None = None
    subcategory: str | None = None
    primary_color: str | None = None
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    shape_tags: list[str] = Field(default_factory=list)
    grade: str | None = None
    handedness: str | None = None
    style: str | None = None
    caption_en: str | None = None
    caption_ko: str | None = None
    source_url: str | None = None
    license: str | None = None


class SearchResponse(BaseModel):
    search_type: str
    query_type: str
    query_text: str | None = None
    # 번역기가 다른 뜻으로 바꾸는 용어를 우회해 영어로 다시 쓴 질의(app/query_terms.py).
    # 재작성하지 않았으면 None이고, 그때는 translated_text가 번역 결과다.
    rewritten_query: str | None = None
    translated_text: str | None = None
    image_weight: float | None = None
    text_weight: float | None = None
    top_k: int
    offset: int
    candidate_count: int
    # 검색 서비스가 실제로 순위를 매기는 상한(MAX_RANKED_RESULTS)까지로 자른 값.
    # candidate_count는 필터를 통과한 전체 개수라 offset+top_k 상한과는 별개다.
    # 프론트엔드는 이 값으로 마지막 페이지를 계산해야 candidate_count가 100을
    # 넘을 때 offset+top_k>100 요청을 만들어 400을 받는 상황을 피할 수 있다.
    retrievable_count: int
    elapsed_ms: float
    search_elapsed_ms: float
    results: list[SearchHit]


class MultimodalWeights(BaseModel):
    image_weight: Annotated[float, Field(ge=0, le=1)] = DEFAULT_IMAGE_WEIGHT
    text_weight: Annotated[float, Field(ge=0, le=1)] = DEFAULT_TEXT_WEIGHT

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        """합이 1이 아닌 값을 조용히 재조정하면 요청한 비율과 실제 검색 비율이 달라진다.

        한쪽만 보내면 나머지가 기본값으로 남아 합이 깨지므로 두 값을 함께 보내야 한다.
        """
        total = self.image_weight + self.text_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "image_weight와 text_weight의 합은 1이어야 합니다: "
                f"{self.image_weight} + {self.text_weight} = {total}"
            )
        return self
