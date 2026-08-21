"""JSONL 메타데이터 조회와 필터 값 표기 정규화를 담당하는 저장소 계층."""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


class AssetRepository:
    """에셋을 메모리에 적재해 ID 조회와 필터 값 정규화를 빠르게 수행한다."""

    # API의 복수형 필드 이름을 실제 메타데이터 키에 연결하는 유일한 매핑이다.
    # 새 필터를 추가할 때 schemas.py와 이 매핑을 함께 변경해야 한다.
    SCALAR_FILTER_FIELDS = {
        "visual_style": "visual_style",
        "category": "category",
        "subcategory": "subcategory",
        "primary_color": "primary_color",
        "grade": "grade",
        "style": "style",
        "handedness": "handedness",
    }
    LIST_FILTER_FIELDS = {
        "colors": "colors",
        "elements": "elements",
        "materials": "materials",
        "shape_tags": "shape_tags",
    }
    TOKEN_SEPARATORS = re.compile(r"[\s\-_]+")

    def __init__(self, metadata_path: Path):
        self.assets: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.by_sha256: dict[str, str] = {}
        with metadata_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                asset = json.loads(line)
                asset_id = asset.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id.strip():
                    raise ValueError(f"메타데이터 {line_number}행에 유효한 asset_id가 없습니다")
                if asset_id in self.by_id:
                    raise ValueError(f"중복 asset_id가 있습니다: {asset_id}")
                self.assets.append(asset)
                self.by_id[asset_id] = asset
                digest = asset.get("sha256")
                if isinstance(digest, str) and digest:
                    self.by_sha256[digest.lower()] = asset_id

        if not self.assets:
            raise ValueError("메타데이터에 검색 가능한 에셋이 없습니다")

        self._filter_vocabulary = self._build_filter_vocabulary()

    @classmethod
    def normalize_token(cls, value: str) -> str:
        """대소문자와 `-`/`_`/공백 표기 차이를 흡수한 비교용 토큰을 만든다."""
        return cls.TOKEN_SEPARATORS.sub("_", value.strip().lower())

    def _build_filter_vocabulary(self) -> dict[str, dict[str, str]]:
        """요청 필드마다 `정규화 토큰 -> 실제 메타데이터 표기`를 만든다.

        한 토큰에 서로 다른 표기가 겹치면 어느 쪽으로 바꿔야 할지 알 수 없으므로
        그 토큰은 사전에서 제외하고 기존의 정확 일치 동작을 유지한다.
        """
        vocabulary: dict[str, dict[str, str]] = {}
        fields = {**self.SCALAR_FILTER_FIELDS, **self.LIST_FILTER_FIELDS}
        for request_field, asset_field in fields.items():
            collected: defaultdict[str, set[str]] = defaultdict(set)
            for asset in self.assets:
                values = asset.get(asset_field, [])
                if not isinstance(values, list):
                    values = [values]
                for value in values:
                    if isinstance(value, str) and value.strip():
                        collected[self.normalize_token(value)].add(value)
            vocabulary[request_field] = {
                token: next(iter(names))
                for token, names in collected.items()
                if len(names) == 1
            }
        return vocabulary

    def get(self, asset_id: str) -> dict | None:
        return self.by_id.get(asset_id)

    def asset_id_for_sha256(self, digest: str) -> str | None:
        return self.by_sha256.get(digest.lower())

    def canonical_value(self, request_field: str, value: str) -> str:
        """메타데이터에 있는 표기를 찾으면 그 표기로, 없으면 입력값 그대로 둔다."""
        vocabulary = self._filter_vocabulary.get(request_field, {})
        return vocabulary.get(self.normalize_token(value), value)

    def canonicalize(self, filters: dict[str, Any]) -> dict[str, Any]:
        """검색 서비스에 넘기기 전에 필터 값을 실제 메타데이터 표기로 맞춘다.

        검색 판정은 `src/retrieval/search_service.py`가 정확 일치로 수행하므로
        `Two-Handed`처럼 표기만 다른 요청은 API 경계에서 한 번만 흡수한다.
        """
        output: dict[str, Any] = {}
        for request_field, value in filters.items():
            if isinstance(value, list):
                output[request_field] = [
                    self.canonical_value(request_field, item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, str):
                output[request_field] = self.canonical_value(request_field, value)
            else:
                output[request_field] = value
        return output

    def filter_coverage(self) -> dict[str, dict[str, int]]:
        """필드별로 값이 있는 에셋 수를 센다.

        `elements`처럼 일부 에셋에만 채워진 속성은 필터를 걸는 순간 후보가 크게
        줄어든다. 필터 UI가 그 사실을 표시할 수 있도록 개수를 제공한다.
        `filter_values`와 응답 모양이 달라 섞으면 필드 목록을 순회하는 쪽이
        깨지므로, API에서도 별도 엔드포인트로 나눠 제공한다.
        """
        coverage: dict[str, dict[str, int]] = {}
        fields = {**self.SCALAR_FILTER_FIELDS, **self.LIST_FILTER_FIELDS}
        for request_field, asset_field in fields.items():
            filled = 0
            for asset in self.assets:
                values = asset.get(asset_field)
                if values not in (None, [], ""):
                    filled += 1
            coverage[request_field] = {
                "assets_with_value": filled,
                "total_assets": len(self.assets),
            }
        coverage["color"] = dict(coverage["colors"])
        coverage["element"] = dict(coverage["elements"])
        return coverage

    def filter_values(self) -> dict[str, list[dict[str, int | str]]]:
        """프론트엔드 필터 UI가 사용할 값과 에셋 개수를 빈도순으로 만든다.

        모든 키가 같은 모양(값 목록)이어야 필터 필드를 순회해 UI를 만들 수 있다.
        """
        output: dict[str, list[dict[str, int | str]]] = {}
        fields = {**self.SCALAR_FILTER_FIELDS, **self.LIST_FILTER_FIELDS}
        for request_field, asset_field in fields.items():
            counts: defaultdict[str, int] = defaultdict(int)
            for asset in self.assets:
                values = asset.get(asset_field, [])
                if not isinstance(values, list):
                    values = [values]
                for value in values:
                    if value is not None:
                        counts[str(value)] += 1
            output[request_field] = [
                {"value": value, "count": count}
                for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]
        output["color"] = list(output["colors"])
        output["element"] = list(output["elements"])
        return output
