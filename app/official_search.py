"""공식 WeaponSearchService를 기존 HTTP 응답·로그 계약에 연결한다."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from app.query_terms import rewrite_korean_query
from app.schemas import MAX_RANKED_RESULTS, SearchFilters


class NoSearchResults(ValueError):
    pass


def image_url(processed_file: str) -> str:
    normalized = processed_file.replace("\\", "/")
    prefix = "data/processed/"
    relative = normalized[len(prefix):] if normalized.startswith(prefix) else normalized
    return f"/images/{relative}"


def result_text_for(asset: dict) -> str:
    return asset.get("caption_ko") or asset.get("caption_en") or asset["asset_id"]


class OfficialSearchAdapter:
    def __init__(self, official_service, repository, log_path: Path):
        self.official_service = official_service
        self.repository = repository
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_lock = threading.Lock()

    @staticmethod
    def filter_dict(filters: SearchFilters) -> dict:
        values = {
            key: value
            for key, value in filters.model_dump().items()
            if value not in (None, [], "")
        }
        if filters.canonical_colors():
            values["colors"] = filters.canonical_colors()
        if filters.canonical_elements():
            values["elements"] = filters.canonical_elements()
        if filters.style:
            values["style"] = filters.style
        if filters.handedness:
            values["handedness"] = filters.handedness
        return values

    def applied_filters(self, filters: SearchFilters) -> dict | None:
        """검색 서비스가 정확 일치로 비교하므로 표기를 메타데이터 쪽에 맞춘다."""
        return self.repository.canonicalize(self.filter_dict(filters)) or None

    def _enrich_hit(self, hit: dict) -> dict:
        asset_id = hit["asset_id"]
        asset = self.repository.get(asset_id)
        if asset is None:
            # 인덱스와 메타데이터가 어긋난 서버 쪽 문제다. ValueError로 두면
            # 엔드포인트의 400 변환에 걸려 클라이언트 잘못처럼 보이므로 500으로
            # 올린다. 시작 시 service_manifest가 두 집합을 대조하므로 평소에는
            # 도달하지 않는다.
            raise RuntimeError(f"검색 결과 메타데이터가 없습니다: {asset_id}")
        output = dict(hit)
        output.update({
            "asset_id": asset_id,
            "image_path": asset["processed_file"],
            "image_url": image_url(asset["processed_file"]),
            "metadata": asset,
            "result_text": result_text_for(asset),
            "color": list(asset.get("colors", [])),
            "element": list(asset.get("elements", [])),
            "source": asset.get("source") or asset.get("source_url"),
        })
        for field in (
            "visual_style", "category", "subcategory", "primary_color",
            "colors", "materials", "elements", "shape_tags", "grade",
            "handedness", "style",
            "caption_en", "caption_ko", "source_url", "license",
        ):
            output[field] = asset.get(field, [] if field in {
                "colors", "materials", "elements", "shape_tags"
            } else None)
        output.setdefault("combined_score", None)
        output.setdefault("image_score", None)
        output.setdefault("text_score", None)
        return output

    def _write_log(
        self, query_type: str, detail: str | None, filters: dict | None,
        top_k: int, offset: int, result_count: int, elapsed_ms: float,
        search_elapsed_ms: float, status_code: int, service_version: str,
        translated_text: str | None, rewritten_query: str | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_type": query_type,
            "detail": detail,
            "translated_text": translated_text,
            # 오역 용어를 우회해 영어로 다시 쓴 질의. 없으면 원문 그대로 검색했다.
            "rewritten_query": rewritten_query,
            # 검색에 실제로 적용된 값만 남긴다. 요청 원문에는 별칭(color/element)과
            # 표기 차이가 섞여 있어 로그만 보고는 결과를 재현할 수 없다.
            "filters": dict(filters or {}),
            "top_k": top_k,
            "offset": offset,
            "result_count": result_count,
            "elapsed_ms": elapsed_ms,
            "search_elapsed_ms": search_elapsed_ms,
            "status_code": status_code,
            "service_version": service_version,
        }
        with self._log_lock, self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def search_query(text: str) -> tuple[str, str | None]:
        """검색에 넘길 질의와, 재작성했다면 그 사실을 함께 돌려준다.

        번역기가 다른 물건으로 바꿔 버리는 용어만 우회한다(app/query_terms.py).
        """
        rewritten = rewrite_korean_query(text)
        return (rewritten or text), rewritten

    def _execute(
        self, call, *, query_type: str, detail: str | None, top_k: int,
        offset: int, filters: dict | None, request_started: float | None,
        service_version: str, query_text: str | None = None,
        rewritten_query: str | None = None,
    ) -> dict:
        search_started = time.perf_counter()
        try:
            payload = call()
        except ValueError as exc:
            if "No assets match" not in str(exc):
                raise
            search_elapsed_ms = round((time.perf_counter() - search_started) * 1000, 3)
            elapsed_ms = round(
                (time.perf_counter() - (request_started or search_started)) * 1000, 3
            )
            self._write_log(
                query_type, detail, filters, top_k, offset, 0, elapsed_ms,
                search_elapsed_ms, 404, service_version, None, rewritten_query,
            )
            raise NoSearchResults("검색 조건에 맞는 결과가 없습니다") from exc

        search_elapsed_ms = round((time.perf_counter() - search_started) * 1000, 3)
        # 서비스에 offset + top_k개를 요청했으므로 앞쪽 페이지를 잘라낸다.
        results = [self._enrich_hit(hit) for hit in payload.get("results", [])[offset:]]
        elapsed_ms = round(
            (time.perf_counter() - (request_started or search_started)) * 1000, 3
        )
        translated = payload.get("translated_text")
        self._write_log(
            query_type, detail, filters, top_k, offset, len(results), elapsed_ms,
            search_elapsed_ms, 200, service_version, translated, rewritten_query,
        )
        return {
            **payload,
            "search_type": payload.get("search_type", query_type),
            "query_type": query_type,
            # 검색에는 재작성한 영어를 쓰더라도 응답에는 사용자가 보낸 원문을 싣는다.
            "query_text": query_text if query_text is not None else payload.get("query_text"),
            "rewritten_query": rewritten_query,
            "translated_text": translated,
            "image_weight": payload.get("image_weight"),
            "text_weight": payload.get("text_weight"),
            "top_k": top_k,
            "offset": offset,
            # 필터를 통과한 전체 개수다. 페이지 길이로 대체하면 프론트엔드가
            # 마지막 페이지를 잘못 계산하므로 검색 서비스가 준 값만 쓴다.
            "candidate_count": payload["candidate_count"],
            # 실제로 offset+top_k로 꺼낼 수 있는 상한. candidate_count가 이보다
            # 커도 그 이상은 400이므로, 마지막 페이지는 이 값 기준으로 계산해야 한다.
            "retrievable_count": min(payload["candidate_count"], MAX_RANKED_RESULTS),
            "elapsed_ms": elapsed_ms,
            "search_elapsed_ms": search_elapsed_ms,
            "results": results,
        }

    def search_text(
        self, query: str, *, top_k: int, offset: int, filters: SearchFilters,
        request_started: float | None, service_version: str,
    ) -> dict:
        applied = self.applied_filters(filters)
        search_text, rewritten = self.search_query(query)
        return self._execute(
            lambda: self.official_service.search_text(
                search_text, top_k=offset + top_k, filters=applied
            ),
            query_type="text", detail=query, top_k=top_k, offset=offset, filters=applied,
            request_started=request_started, service_version=service_version,
            query_text=query, rewritten_query=rewritten,
        )

    def search_image(
        self, image, *, detail: str | None, top_k: int, offset: int,
        filters: SearchFilters, excluded_asset_ids: set[str], include_self: bool,
        request_started: float | None, service_version: str,
    ) -> dict:
        applied = self.applied_filters(filters)
        return self._execute(
            lambda: self.official_service.search_image(
                image, top_k=offset + top_k, filters=applied,
                include_self=include_self,
                excluded_asset_ids=excluded_asset_ids,
            ),
            query_type="image", detail=detail, top_k=top_k, offset=offset, filters=applied,
            request_started=request_started, service_version=service_version,
        )

    def search_multimodal(
        self, image, query: str, *, top_k: int, offset: int, filters: SearchFilters,
        image_weight: float, excluded_asset_ids: set[str],
        request_started: float | None, service_version: str,
    ) -> dict:
        applied = self.applied_filters(filters)
        search_text, rewritten = self.search_query(query)
        return self._execute(
            lambda: self.official_service.search_multimodal(
                image, search_text, top_k=offset + top_k,
                filters=applied,
                image_weight=image_weight,
                excluded_asset_ids=excluded_asset_ids,
            ),
            query_type="multimodal", detail=query, top_k=top_k, offset=offset, filters=applied,
            request_started=request_started, service_version=service_version,
            query_text=query, rewritten_query=rewritten,
        )
