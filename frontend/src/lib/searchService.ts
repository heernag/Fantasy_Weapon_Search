import type {
  ApiSearchHit,
  ApiSearchResponse,
  Asset,
  FilterCatalog,
  SearchFilters,
  SearchRequest,
  SearchResponse
} from "@/src/types/asset";

const apiPrefix = "/api/backend";

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item)) : [];
}

function scorePercent(score: number | null | undefined): number | null {
  if (typeof score !== "number" || !Number.isFinite(score)) return null;
  return Math.round(Math.max(0, Math.min(1, score)) * 100);
}

export function backendUrl(path: string): string {
  if (path.startsWith(apiPrefix)) return path;
  if (path.startsWith("http")) {
    const url = new URL(path);
    return `${apiPrefix}${url.pathname}${url.search}`;
  }
  return `${apiPrefix}${path.startsWith("/") ? path : `/${path}`}`;
}

function assetFromHit(hit: ApiSearchHit): Asset {
  const metadata = hit.metadata ?? {};
  const category = asString(hit.category) ?? asString(metadata.category) ?? "unknown";
  const subcategory = asString(hit.subcategory) ?? asString(metadata.subcategory);
  const colors = hit.colors ?? asStringArray(metadata.colors);
  const elements = hit.elements ?? asStringArray(metadata.elements);
  const materials = hit.materials ?? asStringArray(metadata.materials);
  const shapeTags = hit.shape_tags ?? asStringArray(metadata.shape_tags);
  const score = scorePercent(hit.combined_score ?? hit.score) ?? 0;
  const imageScore = scorePercent(hit.image_score);
  const textScore = scorePercent(hit.text_score);
  const captionKo = asString(hit.caption_ko) ?? asString(metadata.caption_ko);
  const captionEn = asString(hit.caption_en) ?? asString(metadata.caption_en);
  const title = subcategory ?? category;

  return {
    assetId: hit.asset_id,
    title,
    descriptionKo: captionKo ?? captionEn ?? hit.result_text ?? "설명이 제공되지 않았습니다.",
    descriptionEn: captionEn ?? captionKo ?? hit.result_text ?? "No description available.",
    imageUrl: backendUrl(hit.image_url),
    imageWidth: typeof metadata.processed_width === "number" ? metadata.processed_width : 224,
    imageHeight: typeof metadata.processed_height === "number" ? metadata.processed_height : 224,
    category,
    subcategory,
    colors,
    elements,
    materials,
    shapeTags,
    grade: asString(hit.grade) ?? asString(metadata.grade),
    visualStyle: asString(hit.visual_style) ?? asString(metadata.visual_style),
    style: asString(hit.style) ?? asString(metadata.style),
    handedness: asString(hit.handedness) ?? asString(metadata.handedness),
    similarity: score,
    imageSimilarity: imageScore,
    textSimilarity: textScore,
    source: asString(hit.source) ?? asString(metadata.source_name) ?? asString(metadata.source),
    creator: asString(metadata.author),
    sourceUrl: asString(hit.source_url) ?? asString(metadata.source_url),
    license: asString(hit.license) ?? asString(metadata.license),
    licenseStatus: asString(metadata.license_status),
    matchReasons: [
      imageScore === null ? null : `이미지 유사도 ${imageScore}%`,
      textScore === null ? null : `텍스트 유사도 ${textScore}%`,
      colors.length ? `색상: ${colors.slice(0, 2).join(", ")}` : null,
      elements.length ? `속성: ${elements.join(", ")}` : null
    ].filter((reason): reason is string => Boolean(reason))
  };
}

function filtersForApi(filters: SearchFilters): Record<string, string | string[]> {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => (Array.isArray(value) ? value.length > 0 : Boolean(value)))
  ) as Record<string, string | string[]>;
}

function appendFilters(form: FormData, filters: SearchFilters) {
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value) && value.length) form.append(key, value.join(","));
    if (typeof value === "string" && value) form.append(key, value);
  }
}

async function readJson<T>(path: string, init: RequestInit, signal?: AbortSignal): Promise<T> {
  const response = await fetch(backendUrl(path), { ...init, signal, cache: "no-store" });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail?: unknown }).detail : null;
    const message = typeof detail === "string" ? detail : `서버 요청에 실패했습니다. (${response.status})`;
    throw new Error(message);
  }
  return payload as T;
}

export async function fetchFilterCatalog(signal?: AbortSignal): Promise<FilterCatalog> {
  return readJson<FilterCatalog>("/filters", { method: "GET" }, signal);
}

export async function searchAssets(request: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
  const query = request.query.trim();
  let raw: ApiSearchResponse;

  if (request.image) {
    const form = new FormData();
    form.append("image", request.image);
    form.append("top_k", String(request.topK));
    form.append("offset", String(request.offset));
    appendFilters(form, request.filters);

    if (query) {
      form.append("query", query);
      form.append("image_weight", String(request.imageWeight / 100));
      form.append("text_weight", String((100 - request.imageWeight) / 100));
      raw = await readJson<ApiSearchResponse>("/search/multimodal", { method: "POST", body: form }, signal);
    } else {
      raw = await readJson<ApiSearchResponse>("/search/image", { method: "POST", body: form }, signal);
    }
  } else {
    raw = await readJson<ApiSearchResponse>(
      "/search/text",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: request.topK, offset: request.offset, filters: filtersForApi(request.filters) })
      },
      signal
    );
  }

  return {
    results: raw.results.map(assetFromHit),
    totalCount: raw.candidate_count,
    // 마지막 페이지와 다음 버튼은 서버가 보장하는 실제 조회 가능 범위를 사용한다.
    // 구형 서버에 잠시 연결된 경우에도 고정값을 추정하지 않고 현재 응답 결과만 쓴다.
    retrievableCount: Number.isInteger(raw.retrievable_count) ? Math.max(0, raw.retrievable_count) : raw.results.length,
    elapsedMs: Math.round(raw.elapsed_ms),
    searchElapsedMs: Math.round(raw.search_elapsed_ms),
    searchType: raw.search_type,
    queryType: raw.query_type,
    topK: raw.top_k,
    offset: raw.offset
  };
}
