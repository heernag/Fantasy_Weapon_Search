"""HTTP 입력 검증, 애플리케이션 수명주기, 검색 API 라우팅을 담당한다."""

from contextlib import asynccontextmanager
import hashlib
import inspect
import json
import time
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from app.config import get_settings
from app.official_search import NoSearchResults, OfficialSearchAdapter, image_url
from app.repository import AssetRepository
from app.schemas import (
    DEFAULT_IMAGE_WEIGHT,
    DEFAULT_TEXT_WEIGHT,
    MultimodalWeights,
    SearchFilters,
    MAX_RANKED_RESULTS,
    SearchResponse,
    TextSearchRequest,
    validate_page,
)
from app.service_manifest import load_and_validate_service_manifest
from src.retrieval.search_service_adapter import WeaponSearchService


def csv_values(value: str | None) -> list[str]:
    """multipart 폼의 쉼표 구분 필터를 빈 값 없는 목록으로 변환한다."""
    return [item.strip() for item in (value or "").split(",") if item.strip()]


# [의도적 결정] `categories`/`styles`는 SearchFilters에 선언된 필드가 아니라
# before-validator가 단일값으로 접어 주는 이전 프론트엔드 호환 입력이다.
#
# 판단 근거 — 원래는 POST 본문에서만 통하고 GET에서는 조용히 무시됐다. 미지원
# 파라미터를 400으로 돌려주기 시작하면서, 같은 이름이 POST에서는 200이고
# GET에서는 400이 되는 비대칭이 드러났다. 선택지는 (가) 별칭을 폐기하거나
# (나) 네 경로 모두에서 받는 것이었고, (나)를 골랐다. 폐기하면 이미 이 이름을
# 쓰는 클라이언트가 깨지는 반면, 받아주는 쪽은 순수하게 추가라서 깨질 것이
# 없기 때문이다.
#
# 되돌리려면(별칭 폐기) 이 상수를 비우고 `build_filters`의 별칭 병합 루프,
# 네 엔드포인트의 `categories`/`styles` 인자, `SearchFilters`의
# `normalize_legacy_names`, 그리고 이를 쓰는 테스트를 함께 지우면 된다.
# 폐기하면 이 이름으로 보내던 요청은 400을 받는다.
LEGACY_FILTER_NAMES = ("categories", "styles")

# 관리자 대시보드용 평가 지표. frontend 브랜치(backend/app/main.py)에서 이식했다
# (2026-08-28, 동윤 확인). 응답 형식은 원본과 동일하게 유지한다.
#
# 프런트엔드에 공개할 평가 요약은 고정된 파일만 허용한다. 파일명을 요청값으로
# 받으면 data/evaluation 밖의 파일을 노출할 위험이 있어 목록을 코드에 둔다.
EVALUATION_SUMMARY_FILES = {
    "text_search": "evaluation_summary.json",
    "multimodal_test": "multimodal_evaluation_summary.json",
    "multimodal_validation": "multimodal_validation_evaluation_summary.json",
    "illustration_test": "illustration_evaluation_summary.json",
}
EVALUATION_RESULT_FILES = {
    "multimodal_test": "multimodal_test_results_adapter_en.json",
    "multimodal_validation": "multimodal_validation_results_adapter_en.json",
}


def build_filters(**values) -> SearchFilters:
    """선언 필드와 호환 별칭을 합쳐 하나의 필터 모델로 만든다.

    지정하지 않은 필터(None, 빈 목록)는 아예 넘기지 않는다. `category=None`을
    그대로 실으면 별칭 검증이 "값이 지정된 필드"로 보고 `categories`와 충돌한다고
    판단한다.

    다만 빈 문자열은 버리지 않고 그대로 넘겨 400이 나게 둔다. 쿼리스트링과 JSON
    본문에서는 "값을 안 보냄"과 "빈 값을 보냄"이 구분되므로, 빈 값은 클라이언트
    실수로 보고 같은 응답을 준다. 폼은 미입력 필드가 애초에 빈 문자열로 도착해
    둘을 구분할 수 없어서, `form_filters`가 여기 오기 전에 None으로 바꾼다.
    """
    data = {
        key: value
        for key, value in values.items()
        if key not in LEGACY_FILTER_NAMES and value is not None and value != []
    }
    for name in LEGACY_FILTER_NAMES:
        if values.get(name):
            data[name] = values[name]
    return SearchFilters.model_validate(data)


def form_filters(
    visual_style=None,
    category=None,
    subcategory=None,
    primary_color=None,
    grade=None,
    colors=None,
    materials=None,
    elements=None,
    shape_tags=None,
    *,
    color=None,
    element=None,
    material=None,
    style=None,
    handedness=None,
    categories=None,
    styles=None,
):
    """이미지 계열 엔드포인트의 폼 필터를 공통 Pydantic 모델로 맞춘다."""
    return build_filters(
        visual_style=visual_style or None,
        category=category or None,
        subcategory=subcategory or None,
        primary_color=primary_color or None,
        grade=grade or None,
        colors=csv_values(colors),
        elements=csv_values(elements),
        materials=csv_values(materials or material),
        shape_tags=csv_values(shape_tags),
        color=csv_values(color) or None,
        element=csv_values(element) or None,
        style=style or None,
        handedness=handedness or None,
        categories=csv_values(categories),
        styles=csv_values(styles),
    )


def reject_unknown_parameters(received, endpoint) -> None:
    """선언되지 않은 이름을 조용히 무시하지 않고 인수인계 문서의 400으로 돌려준다.

    허용 목록을 따로 두면 엔드포인트 인자와 어긋나므로 서명에서 직접 읽는다.
    """
    declared = {name for name in inspect.signature(endpoint).parameters if name != "request"}
    unknown = sorted(set(received) - declared)
    if unknown:
        raise HTTPException(400, f"지원하지 않는 파라미터입니다: {', '.join(unknown)}")


def request_page(top_k: int, offset: int) -> None:
    """폼 요청의 페이지 범위를 JSON 요청과 같은 400 계약으로 검증한다."""
    if not 1 <= top_k <= MAX_RANKED_RESULTS:
        raise HTTPException(400, f"top_k는 1~{MAX_RANKED_RESULTS}이어야 합니다")
    if offset < 0:
        raise HTTPException(400, "offset은 0 이상이어야 합니다")
    try:
        validate_page(top_k, offset)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def request_filters(**values) -> SearchFilters:
    """필터 검증 실패를 인수인계 문서 10절의 HTTP 400 계약으로 바꾼다.

    SearchFilters의 충돌 검증은 pydantic 예외로 올라오므로, 엔드포인트가
    직접 모델을 만들면 500이 된다. 요청 경로는 모두 이 함수를 거친다.
    """
    try:
        return build_filters(**values)
    except ValidationError as exc:
        raise HTTPException(400, str(exc)) from exc


def request_form_filters(*args, **kwargs) -> SearchFilters:
    """폼 검증 실패를 인수인계 문서 10절의 HTTP 400 계약으로 바꾼다."""
    try:
        return form_filters(*args, **kwargs)
    except ValidationError as exc:
        raise HTTPException(400, str(exc)) from exc


async def read_image(upload: UploadFile) -> tuple[Image.Image, str]:
    """업로드 크기·MIME·실제 디코딩을 검증하고 RGB 이미지로 반환한다."""
    if upload.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "PNG, JPEG, WEBP 이미지만 업로드할 수 있습니다")
    raw = await upload.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "이미지는 10MB 이하여야 합니다")
    try:
        image = Image.open(BytesIO(raw))
        image.load()
        return image.convert("RGB"), hashlib.sha256(raw).hexdigest()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(400, "손상되었거나 지원되지 않는 이미지입니다") from exc


def image_files(settings, repository) -> dict[str, Path]:
    """`/images` URL을 최종 메타데이터에 있는 파일로만 연결한다."""
    root = settings.absolute(settings.image_root)
    prefix = "/images/"
    return {
        image_url(asset["processed_file"]).removeprefix(prefix): root / asset["processed_file"]
        for asset in repository.assets
    }


def create_search_service(settings):
    """검색 모델을 API 프로세스 안에 직접 올린다.

    [과제 정의서 대비 해석] 초기 설계 문서의 3번 담당 항목에는 "모델 서버 연동"이
    있는데, 지금 구현은 별도 모델 서버를 두지 않고 이 프로세스가 모델을 직접
    로딩한다. 그렇게 정한 근거는 둘이다.

    1. AI 담당의 인수인계 메모와 docs/CUSTOM_ADAPTER_HANDOFF_KO.md가 "서비스는 API 시작 시
       한 번만 생성하고 요청마다 재사용한다"고 지시한다. 별도 서버가 아니라 같은
       프로세스에서 객체를 재사용하는 형태를 전제한 문구다.
    2. 어댑터 서비스는 OpenCLIP 가중치·어댑터 체크포인트·FAISS 인덱스·메타데이터를
       한 객체가 함께 들고 있다(src/retrieval/search_service_adapter.py). 모델만
       떼어내면 인덱스와 임베딩의 소유 위치도 함께 옮겨간다.

    별도 모델 서버로 분리하기로 하면 —
    - 바꿀 지점은 이 함수 하나다. WeaponSearchService 대신 같은 메서드 이름
      (search_text / search_image / search_multimodal)을 HTTP로 호출하는 클라이언트
      객체를 돌려주면, app/official_search.py 아래 계층은 그대로 둬도 된다.
    - 다만 /health가 읽는 `faiss_index.ntotal`/`.d`(app/main.py)와 기동 시
      service_manifest 검증(app/service_manifest.py의 `_index_and_ids`)이 인덱스
      객체에 직접 접근하므로, 원격 서비스라면 이 두 곳을 원격 조회로 바꿔야 한다.
    - 인덱스를 API 쪽에 두느냐 모델 서버 쪽에 두느냐에 따라 위 두 지점의 구현이
      달라진다.
    """
    return WeaponSearchService(
        root=settings.project_root,
        device=settings.device,
        enable_korean_translation=True,
    )


def preload_translation_service(official_service, settings) -> bool:
    """설정에 따라 요청을 받기 전에 한국어 번역 모델을 미리 태운다.

    번역 모델(`src/retrieval/search_service.py`의 `_load_translation_model`)은
    지연 로딩이고 lock이 없다. 첫 한국어 검색이 모델을 내려받고 초기화하는
    수 초~수십 초를 그대로 사용자에게 노출하고, 그 사이 동시에 들어온 한국어
    요청은 로딩을 중복 시도할 수 있다.

    이 함수는 `search_text`라는 공개 메서드를 한 번 호출해 로딩을 강제한다.
    ASGI lifespan은 startup이 끝나야 요청을 받기 시작하므로, 여기서 동기적으로
    실행하면 실제 트래픽이 도달하는 시점에는 이미 로딩이 끝나 있다. 로딩이
    끝난 뒤에는 지연 로딩의 확인-후-로드 검사가 즉시 반환되므로, 동시 요청
    경합 창도 함께 사라진다. `src/retrieval/search_service.py`는 고치지 않았다.

    기본값은 꺼져 있다(`FWS_PRELOAD_TRANSLATION_MODEL`). 로컬 개발·테스트에서
    서버(TestClient 포함)를 반복 기동할 때마다 이 비용을 물지 않기 위해서다.
    """
    if not settings.preload_translation_model:
        return False
    official_service.search_text("판타지 무기 검색 서비스 준비 확인용 문장입니다.", top_k=1)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """요청마다 재로딩하지 않도록 무거운 모델과 인덱스를 시작 시 한 번 준비한다."""
    settings = get_settings()
    repository = AssetRepository(settings.absolute(settings.metadata_path))
    official_service = create_search_service(settings)
    service_manifest = load_and_validate_service_manifest(settings, repository, official_service)
    app.state.repository = repository
    app.state.official_search_service = official_service
    app.state.search = OfficialSearchAdapter(
        official_service, repository, settings.absolute(settings.log_path)
    )
    app.state.service_manifest = service_manifest
    app.state.image_files = image_files(settings, repository)
    # 매니페스트 검증(빠른 무결성 확인)이 끝난 뒤에 번역 모델 로딩(느릴 수 있음)을
    # 시도한다. 손상된 번들을 굳이 다운로드가 끝난 뒤에야 알아채지 않기 위해서다.
    app.state.translation_preloaded = preload_translation_service(official_service, settings)
    yield


settings = get_settings()
app = FastAPI(title="Fantasy Weapon Search API", version="1.0.0", lifespan=lifespan)


def load_evaluation_summaries() -> dict[str, dict]:
    """프런트엔드용 평가 요약 JSON을 고정된 목록에서 읽는다."""
    evaluation_root = settings.absolute(Path("data/evaluation"))
    try:
        return {
            key: json.loads((evaluation_root / filename).read_text(encoding="utf-8"))
            for key, filename in EVALUATION_SUMMARY_FILES.items()
        }
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("평가 요약 데이터를 읽을 수 없습니다") from exc


def load_evaluation_metrics() -> dict:
    """실측된 결과 파일에서 품질 지표만 공개한다.

    nDCG, 지연 시간, 무결과율, 실패 쿼리는 현재 결과 파일에 없으므로 null/빈 목록으로
    반환한다. 대시보드가 추정값을 실제 측정값처럼 표시하지 않게 하는 계약이다.
    """
    try:
        result_root = settings.absolute(Path("results"))
        quality_sets = []
        result_documents = {}
        for key, filename in EVALUATION_RESULT_FILES.items():
            document = json.loads((result_root / filename).read_text(encoding="utf-8"))
            result_documents[key] = document
            selected_weight = document.get("selected_weight", document.get("fixed_weight", {}))
            chosen_weight = selected_weight.get("image_weight")
            row = next((item for item in document.get("weight_results", []) if item.get("image_weight") == chosen_weight), None)
            if row is None:
                row = document.get("weight_results", [None])[0]
            overall = (row or {}).get("overall", document.get("overall", {})) if isinstance(row, dict) else document.get("overall", {})
            quality_sets.append({
                "dataset": key,
                "query_count": overall.get("query_count"),
                "recall_at_1": overall.get("Recall@1"),
                "recall_at_5": overall.get("Recall@5"),
                "recall_at_10": overall.get("Recall@10"),
                "mrr": overall.get("MRR"),
                "ndcg": overall.get("nDCG@10"),
                "map": overall.get("mAP"),
                "image_weight": chosen_weight,
            })
        validation = next((item for item in quality_sets if item["dataset"] == "multimodal_validation"), {})
        validation_document = result_documents.get("multimodal_validation", {})
        validation_weight = validation_document.get("selected_weight", {}).get("image_weight")
        validation_rows = validation_document.get("weight_results", [])
        selected_validation_row = next((row for row in validation_rows if row.get("image_weight") == validation_weight), validation_rows[0] if validation_rows else {})

        def mode_payload(key, label, row):
            overall = row.get("overall", {})
            return {
                "key": key,
                "label": label,
                "image_weight": row.get("image_weight"),
                "text_weight": row.get("text_weight"),
                "query_count": overall.get("query_count"),
                "recall": {"1": overall.get("Recall@1"), "5": overall.get("Recall@5"), "10": overall.get("Recall@10")},
                "metrics": {"map": overall.get("mAP"), "recall_at_10": overall.get("Recall@10"), "mrr": overall.get("MRR"), "ndcg_at_10": overall.get("nDCG@10")},
            }

        mode_rows = {
            "image": next((row for row in validation_rows if row.get("image_weight") == 1.0), {}),
            "text": next((row for row in validation_rows if row.get("image_weight") == 0.0), {}),
            "multimodal": selected_validation_row,
        }
        selected_log = result_root / "multimodal_validation_results_adapter_en_query_logs.jsonl"
        logs = [json.loads(line) for line in selected_log.read_text(encoding="utf-8").splitlines() if line.strip()] if selected_log.exists() else []
        query_path = settings.absolute(Path("data/evaluation/multimodal_validation_queries.jsonl"))
        dimensions = {record["query_id"]: record for record in (json.loads(row) for row in query_path.read_text(encoding="utf-8").splitlines() if row.strip())}
        def grouped(field):
            groups = {}
            for log in logs:
                value = dimensions.get(log["query_id"], {}).get(field)
                for item in value if isinstance(value, list) else [value]:
                    if item is not None: groups.setdefault(item, []).append(log)
            return {key: {"query_count": len(rows), "recall_at_10": sum(row["first_relevant_rank"] is not None and row["first_relevant_rank"] <= 10 for row in rows) / len(rows), "mrr": sum(1 / row["first_relevant_rank"] if row["first_relevant_rank"] else 0 for row in rows) / len(rows)} for key, rows in groups.items()}
        latencies = sorted(row["search_elapsed_ms"] for row in logs)
        failures = [{"query_id": row["query_id"], "query": row["query_text"], "query_type": row["query_type"], "top_results": row["top_results"], "relevant_asset_ids": row["relevant_asset_ids"], "first_relevant_rank": row["first_relevant_rank"], "reason": "no relevant asset in ranked results"} for row in logs if not row["success"]]
        history_path = result_root / "evaluation_history.jsonl"
        history_rows = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()] if history_path.exists() else []
        # 추이 그래프는 날짜 단위 비교이므로, 과거에 중복 저장된 행이 있어도
        # 같은 날짜의 가장 최근 멀티모달 검증 결과만 반환한다.
        history_by_date = {
            row["date"]: row
            for row in history_rows
            if row.get("dataset") == "multimodal_validation" and row.get("date")
        }
        history = [history_by_date[key] for key in sorted(history_by_date)]
        return {
            "quality_sets": quality_sets,
            "zero_result_rate": sum(row["zero_result"] for row in logs) / len(logs) if logs else None,
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "p95_latency_ms": latencies[min(len(latencies) - 1, int(len(latencies) * .95))] if latencies else None,
            "failed_queries": failures,
            "trend": history,
            "mode_comparison": [
                mode_payload("image", "이미지 전용", mode_rows["image"]),
                mode_payload("text", "텍스트 전용", mode_rows["text"]),
                mode_payload("multimodal", "이미지 + 텍스트", mode_rows["multimodal"]),
            ],
            "by_query_type": selected_validation_row.get("by_query_type", {}),
            "by_dimension": {"weapon_category": grouped("weapon_category"), "primary_color": grouped("target_primary_color"), "elements": grouped("target_elements")},
        }
    except (OSError, json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError("평가 지표 데이터를 읽을 수 없습니다") from exc


def configure_cors(target_app: FastAPI, origins: list[str]) -> None:
    if not origins:
        return
    target_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


configure_cors(app, settings.cors_origin_list)


@app.middleware("http")
async def record_request_start(request: Request, call_next):
    request.state.request_started = time.perf_counter()
    return await call_next(request)


@app.exception_handler(NoSearchResults)
async def no_search_results_handler(_request: Request, exc: NoSearchResults):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, exc: RequestValidationError):
    """Expose FastAPI/Pydantic input failures using the handoff HTTP 400 contract."""
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


# 최종 데이터는 pixel_art, illustration, rendered_icon을 data/processed 아래의
# 하위 폴더로 구분한다. 디렉터리를 통째로 mount하면 최종 번들에 없는 작업 파일까지
# 함께 공개되므로, 메타데이터에 실린 파일만 URL로 제공한다.
@app.get("/images/{image_path:path}")
def image_file(image_path: str, request: Request):
    resolved = request.app.state.image_files.get(image_path)
    if resolved is None:
        raise HTTPException(404, "이미지를 찾을 수 없습니다")
    return FileResponse(resolved)


@app.get("/", include_in_schema=False)
def root():
    """루트 주소를 API 문서로 보낸다.

    브라우저 주소창에 http://127.0.0.1:8000 만 입력하는 것이 자연스럽고
    run_server.cmd 배너도 그 주소를 안내한다. 이 라우트가 없으면 첫 접속이
    404가 되어 서버가 고장난 것처럼 보인다. 실제 API 계약은 아니므로
    include_in_schema=False로 두어 OpenAPI 문서에는 넣지 않는다.
    """
    return RedirectResponse(url="/docs")


@app.get("/health")
def health(request: Request):
    manifest = request.app.state.service_manifest
    return {
        "status": "ok",
        "assets": len(request.app.state.repository.assets),
        "vectors": request.app.state.official_search_service.faiss_index.ntotal,
        "vector_dimension": request.app.state.official_search_service.faiss_index.d,
        "model": {
            "name": settings.model_name,
            "pretrained": settings.pretrained,
            "integration_status": "final_adapter",
        },
        "service_version": manifest["service_version"],
        # lifespan startup이 끝나야 요청을 받으므로 이 엔드포인트가 응답한다는
        # 것 자체가 검색 가능한 상태라는 뜻이다. 이 값은 번역 모델을 실제로
        # 미리 태웠는지(FWS_PRELOAD_TRANSLATION_MODEL)만 별도로 알려준다 —
        # 꺼져 있으면 서비스는 정상이되 첫 한국어 검색만 느릴 수 있다.
        "translation_preloaded": request.app.state.translation_preloaded,
    }


@app.get("/filters")
def filters(request: Request):
    return request.app.state.repository.filter_values()


@app.get("/filters/coverage")
def filter_coverage(request: Request):
    """필드별로 값이 채워진 에셋 수. `elements`처럼 일부만 태깅된 속성을 UI가 알린다."""
    return request.app.state.repository.filter_coverage()


@app.get("/evaluation/summary")
def evaluation_summary():
    """텍스트·멀티모달·일러스트 평가의 요약 JSON을 한 번에 반환한다."""
    try:
        return load_evaluation_summaries()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/evaluation/metrics")
def evaluation_metrics():
    """대시보드용 검색 품질·운영 지표를 반환한다."""
    try:
        return load_evaluation_metrics()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/assets/{asset_id}")
def asset(asset_id: str, request: Request):
    found = request.app.state.repository.get(asset_id)
    if not found:
        raise HTTPException(404, "에셋을 찾을 수 없습니다")
    return {
        "asset_id": asset_id,
        "image_url": image_url(found["processed_file"]),
        "metadata": found,
    }


def run_text_search(
    request: Request, query: str, top_k: int, offset: int, filters: SearchFilters
):
    service = request.app.state.search
    try:
        return service.search_text(
            query, top_k=top_k, offset=offset, filters=filters,
            request_started=request.state.request_started,
            service_version=request.app.state.service_manifest["service_version"],
        )
    except NoSearchResults:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/search/text", response_model=SearchResponse)
def search_text_get(
    request: Request,
    query: str = Query(min_length=1, max_length=500),
    top_k: int = Query(10, ge=1, le=MAX_RANKED_RESULTS),
    offset: int = Query(0, ge=0, le=MAX_RANKED_RESULTS - 1),
    visual_style: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    primary_color: str | None = None,
    grade: str | None = None,
    colors: list[str] = Query(default=[]),
    materials: list[str] = Query(default=[]),
    elements: list[str] = Query(default=[]),
    shape_tags: list[str] = Query(default=[]),
    color: list[str] = Query(default=[]),
    element: list[str] = Query(default=[]),
    style: str | None = None,
    handedness: str | None = None,
    categories: list[str] = Query(default=[]),
    styles: list[str] = Query(default=[]),
):
    reject_unknown_parameters(request.query_params, search_text_get)
    request_page(top_k, offset)
    filters = request_filters(
        visual_style=visual_style, category=category, subcategory=subcategory,
        primary_color=primary_color, grade=grade, colors=colors, materials=materials,
        elements=elements, shape_tags=shape_tags, color=color or None, element=element or None,
        style=style, handedness=handedness, categories=categories, styles=styles,
    )
    return run_text_search(request, query.strip(), top_k, offset, filters)


@app.post("/search/text", response_model=SearchResponse)
def search_text_post(body: TextSearchRequest, request: Request):
    return run_text_search(request, body.query, body.top_k, body.offset, body.filters)


@app.post("/search/image", response_model=SearchResponse)
async def search_image(
    request: Request,
    image: UploadFile = File(...),
    top_k: int = Form(10),
    offset: int = Form(0),
    include_self: bool = Form(False),
    visual_style: str = Form(""), category: str = Form(""), subcategory: str = Form(""),
    primary_color: str = Form(""), grade: str = Form(""), colors: str = Form(""),
    materials: str = Form(""), elements: str = Form(""), shape_tags: str = Form(""),
    color: str = Form(""), element: str = Form(""), material: str = Form(""),
    style: str = Form(""), handedness: str = Form(""),
    categories: str = Form(""), styles: str = Form(""),
):
    reject_unknown_parameters(await request.form(), search_image)
    request_page(top_k, offset)
    service = request.app.state.search
    pil_image, digest = await read_image(image)
    fs = request_form_filters(
        visual_style, category, subcategory, primary_color, grade, colors, materials,
        elements, shape_tags, color=color, element=element, material=material,
        style=style, handedness=handedness, categories=categories, styles=styles,
    )
    matched_id = request.app.state.repository.asset_id_for_sha256(digest)
    excluded = set() if include_self or matched_id is None else {matched_id}
    try:
        return service.search_image(
            pil_image, detail=image.filename, top_k=top_k, offset=offset, filters=fs,
            excluded_asset_ids=excluded, include_self=include_self,
            request_started=request.state.request_started,
            service_version=request.app.state.service_manifest["service_version"],
        )
    except NoSearchResults:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/search/multimodal", response_model=SearchResponse)
async def search_multimodal(
    request: Request,
    image: UploadFile = File(...),
    query: str = Form(...),
    image_weight: float = Form(DEFAULT_IMAGE_WEIGHT),
    text_weight: float = Form(DEFAULT_TEXT_WEIGHT),
    top_k: int = Form(10),
    offset: int = Form(0),
    include_self: bool = Form(False),
    visual_style: str = Form(""), category: str = Form(""), subcategory: str = Form(""),
    primary_color: str = Form(""), grade: str = Form(""), colors: str = Form(""),
    materials: str = Form(""), elements: str = Form(""), shape_tags: str = Form(""),
    color: str = Form(""), element: str = Form(""), material: str = Form(""),
    style: str = Form(""), handedness: str = Form(""),
    categories: str = Form(""), styles: str = Form(""),
):
    reject_unknown_parameters(await request.form(), search_multimodal)
    if not query.strip():
        raise HTTPException(400, "query가 비어 있습니다")
    request_page(top_k, offset)
    try:
        weights = MultimodalWeights(image_weight=image_weight, text_weight=text_weight)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    service = request.app.state.search
    pil_image, digest = await read_image(image)
    fs = request_form_filters(
        visual_style, category, subcategory, primary_color, grade, colors, materials,
        elements, shape_tags, color=color, element=element, material=material,
        style=style, handedness=handedness, categories=categories, styles=styles,
    )
    matched_id = request.app.state.repository.asset_id_for_sha256(digest)
    excluded = set() if include_self or matched_id is None else {matched_id}
    try:
        return service.search_multimodal(
            pil_image, query, top_k=top_k, offset=offset, filters=fs,
            image_weight=weights.image_weight,
            excluded_asset_ids=excluded,
            request_started=request.state.request_started,
            service_version=request.app.state.service_manifest["service_version"],
        )
    except NoSearchResults:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
