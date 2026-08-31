"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AssetDetail } from "@/src/components/AssetDetail";
import { FilterPanel } from "@/src/components/FilterPanel";
import { ResultCard } from "@/src/components/ResultCard";
import { displayValue, filterLabels, type Locale } from "@/src/lib/labels";
import { fetchFilterCatalog, searchAssets } from "@/src/lib/searchService";
import { emptyFilters, listFilterKeys, type Asset, type FilterCatalog, type FilterKey, type SearchFilters, type SearchRequest, type SearchResponse } from "@/src/types/asset";

const resultPageSize = 24;

function selectedFilterCount(filters: SearchFilters) {
  return Object.values(filters).reduce((count, value) => count + (Array.isArray(value) ? value.length : Number(Boolean(value))), 0);
}

export default function HomePage() {
  const [locale, setLocale] = useState<Locale>("ko");
  const copy = locale === "ko" ? { imageTuning: "검색 기준 조절", tuningDescription: "참고 이미지의 형태를 유지할수록 이미지 비중을 높이세요.", image: "이미지", text: "텍스트", imageFirst: "이미지 우선 · 형태 유지", textFirst: "텍스트 우선 · 색상·속성 반영", setting: "현재 설정", shown: "표시 결과", response: "전체 응답", operation: "검색 연산", previous: "이전", next: "다음", empty: "검색어 또는 참고 이미지를 입력해 주세요.", noResults: "조건과 일치하는 에셋이 없습니다.", emptyHelp: "백엔드의 실제 검색 인덱스를 사용합니다.", noResultsHelp: "필터를 일부 지우거나 다른 검색어를 사용해 보세요.", resetFilters: "필터 초기화", status: "개발 상태", statusText: "FastAPI 검색 API · 실제 이미지 · 실제 메타데이터 연결됨", filter: "필터", applyFilters: "필터 적용하기", closeFilters: "필터 닫기" } : { imageTuning: "Search weighting", tuningDescription: "Increase image weight to preserve the reference image shape.", image: "Image", text: "Text", imageFirst: "Image first · preserve shape", textFirst: "Text first · apply color & elements", setting: "Current setting", shown: "Shown", response: "Total response", operation: "Search operation", previous: "Previous", next: "Next", empty: "Enter a search query or reference image.", noResults: "No assets match these conditions.", emptyHelp: "Uses the backend search index.", noResultsHelp: "Clear some filters or try another query.", resetFilters: "Reset filters", status: "Development status", statusText: "FastAPI Search API · live images · live metadata", filter: "Filters", applyFilters: "Apply filters", closeFilters: "Close filters" };
  const [query, setQuery] = useState("");
  const [image, setImage] = useState<File | undefined>();
  const [imageWeight, setImageWeight] = useState(40);
  const [filters, setFilters] = useState<SearchFilters>(emptyFilters);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [filterCatalog, setFilterCatalog] = useState<FilterCatalog | null>(null);
  const [isFilterCatalogLoading, setFilterCatalogLoading] = useState(true);
  const [hasFilterCatalogError, setFilterCatalogError] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryRequest, setRetryRequest] = useState<SearchRequest | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [isMobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [filterCollapseVersion, setFilterCollapseVersion] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestSequence = useRef(0);
  const activeRequestSignature = useRef<string | null>(null);

  const selectedCount = useMemo(() => selectedFilterCount(filters), [filters]);
  const mode = image && query.trim() ? (locale === "ko" ? "결합 검색" : "Combined search") : image ? (locale === "ko" ? "이미지 검색" : "Image search") : (locale === "ko" ? "텍스트 검색" : "Text search");
  const activeFilterValues = useMemo(() => Object.entries(filters).flatMap(([key, value]) => (Array.isArray(value) ? value.map((item) => ({ key: key as FilterKey, value: item })) : value ? [{ key: key as FilterKey, value }] : [])), [filters]);

  useEffect(() => { document.documentElement.lang = locale; }, [locale]);

  const reloadFilterCatalog = async () => {
    setFilterCatalogLoading(true);
    setFilterCatalogError(false);
    try {
      setFilterCatalog(await fetchFilterCatalog());
    } catch {
      setFilterCatalog(null);
      setFilterCatalogError(true);
    } finally {
      setFilterCatalogLoading(false);
    }
  };

  useEffect(() => {
    let isActive = true;
    void fetchFilterCatalog().then((catalog) => {
      if (isActive) setFilterCatalog(catalog);
    }).catch(() => {
      if (isActive) setFilterCatalogError(true);
    }).finally(() => {
      if (isActive) setFilterCatalogLoading(false);
    });
    return () => { isActive = false; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedAsset(null);
        setMobileFiltersOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const runSearch = async (next: Partial<SearchRequest> = {}, showValidationError = true) => {
    const requestedOffset = next.offset ?? 0;
    const knownRetrievableCount = response?.retrievableCount;
    const remainingResults = knownRetrievableCount === undefined ? resultPageSize : Math.max(0, knownRetrievableCount - requestedOffset);
    const request: SearchRequest = { query, image, imageWeight, filters, offset: requestedOffset, topK: next.topK ?? Math.max(1, Math.min(resultPageSize, remainingResults)), ...next };
    if (!request.query.trim() && !request.image) {
      if (showValidationError) setError(locale === "ko" ? "검색어를 입력하거나 참고 이미지를 선택해 주세요." : "Enter a search query or reference image.");
      return;
    }

    const imageKey = request.image ? `${request.image.name}-${request.image.size}-${request.image.lastModified}` : "no-image";
    const signature = JSON.stringify({ query: request.query, imageKey, imageWeight: request.imageWeight, filters: request.filters, topK: request.topK, offset: request.offset });
    if (activeRequestSignature.current === signature) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const sequence = ++requestSequence.current;
    activeRequestSignature.current = signature;
    setRetryRequest(request);
    setError("");
    // 새 검색이 시작되면 이전 결과를 즉시 비웁니다. 결과 없음/오류 응답에
    // 직전 검색 카드와 응답 시간이 남아 보이는 것을 방지합니다.
    setResponse(null);
    setIsLoading(true);
    setHasSearched(true);

    try {
      const nextResponse = await searchAssets(request, controller.signal);
      if (sequence === requestSequence.current) setResponse(nextResponse);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      if (sequence === requestSequence.current) {
        setResponse(null);
        setError(locale === "ko" ? "검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." : "We could not load search results. Please try again shortly.");
      }
    } finally {
      if (sequence === requestSequence.current) {
        activeRequestSignature.current = null;
        setIsLoading(false);
      }
    }
  };

  const updateFilters = (key: FilterKey, value: string) => {
    const isList = (listFilterKeys as readonly string[]).includes(key);
    const nextFilters: SearchFilters = {
      ...filters,
      [key]: isList
        ? (filters[key] as string[]).includes(value)
          ? (filters[key] as string[]).filter((item) => item !== value)
          : [...(filters[key] as string[]), value]
        : filters[key] === value
          ? null
          : value
    } as SearchFilters;
    if (key === "category") nextFilters.subcategory = null;
    setFilters(nextFilters);
    if (query.trim() || image) void runSearch({ filters: nextFilters, offset: 0 }, false);
  };

  const resetFilters = () => {
    setFilters(emptyFilters);
    if (query.trim() || image) void runSearch({ filters: emptyFilters, offset: 0 }, false);
  };

  const handleFile = (file?: File) => {
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setError(locale === "ko" ? "지원하지 않는 형식입니다. PNG, JPG, WEBP 이미지를 선택해 주세요." : "Unsupported format. Choose a PNG, JPG, or WEBP image.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError(locale === "ko" ? "이미지는 10MB 이하여야 합니다." : "The image must be 10 MB or smaller.");
      return;
    }
    setImage(file);
    setError("");
  };

  const clearImage = () => {
    setImage(undefined);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const searchSimilar = async (asset: Asset) => {
    setSelectedAsset(null);
    setError("");
    try {
      const imageResponse = await fetch(asset.imageUrl);
      if (!imageResponse.ok) throw new Error("원본 에셋 이미지를 불러오지 못했습니다.");
      const blob = await imageResponse.blob();
      const similarImage = new File([blob], `${asset.assetId}.png`, { type: blob.type || "image/png" });
      setImage(similarImage);
      setImageWeight(100);
      setQuery("");
      await runSearch({ image: similarImage, imageWeight: 100, query: "", offset: 0 });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "유사 에셋 검색을 시작하지 못했습니다.");
    }
  };

  const resetSearch = () => {
    abortRef.current?.abort();
    requestSequence.current += 1;
    activeRequestSignature.current = null;
    setQuery("");
    clearImage();
    setImageWeight(40);
    setFilters(emptyFilters);
    setResponse(null);
    setHasSearched(false);
    setIsLoading(false);
    setError("");
    setRetryRequest(null);
    setSelectedAsset(null);
    setMobileFiltersOpen(false);
  };

  const resetToHome = () => {
    resetSearch();
    setFilterCollapseVersion((version) => version + 1);
  };

  const rankedResultCount = response?.retrievableCount ?? 0;
  const canGoPrevious = Boolean(response && response.offset > 0 && !isLoading);
  const canGoNext = Boolean(response && !isLoading && response.offset + response.results.length < rankedResultCount);
  const hasNoResultResponse = hasSearched && !isLoading && !response;

  return (
    <main id="main-content">
      <header className="app-header">
        <a className="brand" href="#top" aria-label="Fantasy Weapon Search home" translate="no" onClick={resetToHome}><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="m14.7 3.1 6.2 6.2-1.5 1.5-1.1-1.1-8.9 8.9v2.3H7.1v-2.3l8.9-8.9-1.1-1.1 1.5-1.5-1.7-1.7-8.8 8.8-1.6-1.6L13 4.8l1.7-1.7Z" /><path d="m3.2 20.8 3.5-3.5" /></svg></span><span>Fantasy Weapon Search</span></a>
        <nav aria-label={locale === "ko" ? "주요 탐색" : "Main navigation"}><Link className="nav-button is-active" href="/">{locale === "ko" ? "검색" : "Search"}</Link></nav>
        <label className="language-switch"><span className="sr-only">Language</span><select name="language" value={locale} onChange={(event) => setLocale(event.target.value as Locale)}><option value="ko">한국어</option><option value="en">English</option></select></label>
      </header>
      <div id="top" className="app-layout">
        <div className="desktop-filters"><FilterPanel key={`desktop-${filterCollapseVersion}`} catalog={filterCatalog} collapseVersion={filterCollapseVersion} error={hasFilterCatalogError} filters={filters} isLoading={isFilterCatalogLoading} locale={locale} onChange={updateFilters} onReload={() => void reloadFilterCatalog()} onReset={resetFilters} /></div>
        <section className="search-content" aria-labelledby="search-title">
          <header className="search-hero"><span className="section-label">{locale === "ko" ? "멀티모달 에셋 탐색" : "Multimodal asset discovery"}</span><h1 id="search-title">{locale === "ko" ? "어떤 무기를 찾고 있나요?" : "Which weapon are you looking for?"}</h1><p>{locale === "ko" ? "텍스트, 참고 이미지, 또는 두 조건을 함께 사용해 보세요." : "Search with text, a reference image, or both."}</p></header>
          <section className="search-panel" aria-label={locale === "ko" ? "검색 조건" : "Search controls"}>
            <form id="asset-search-form" onSubmit={(event) => { event.preventDefault(); void runSearch(); }}>
              <label className="search-input-wrap"><span className="sr-only">{locale === "ko" ? "자연어 검색" : "Natural-language search"}</span><span aria-hidden="true">⌕</span><input name="search-query" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === "ko" ? "예: 푸른 마법이 깃든 판타지 양손검…" : "e.g. blue enchanted fantasy greatsword…"} /></label>
            </form>
            <div className="example-row"><span>{locale === "ko" ? "예시" : "Examples"}</span>{(locale === "ko" ? ["파란 얼음 검", "금색 불 속성 무기", "픽셀아트 단검"] : ["Blue ice sword", "Golden fire weapon", "Pixel-art dagger"]).map((example) => <button type="button" key={example} className="query-chip" disabled={isLoading} onClick={() => { setQuery(example); void runSearch({ query: example, offset: 0 }); }}>{example}</button>)}</div>
            <div className="input-row">
              <div className="upload-zone"><input ref={fileInputRef} id="reference-image" name="reference-image" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleFile(event.target.files?.[0])} /><label htmlFor="reference-image"><span className="upload-icon" aria-hidden="true">↑</span><span><strong>{image ? image.name : locale === "ko" ? "참고 이미지 추가 (선택)" : "Add reference image (optional)"}</strong><small>{image ? (locale === "ko" ? "실제 이미지 파일이 검색 요청에 포함됩니다" : "The image will be included in the search request") : "PNG, JPG, WEBP · max 10 MB"}</small></span></label>{image && <button type="button" className="clear-image" onClick={clearImage}>{locale === "ko" ? "제거" : "Remove"}</button>}</div>
              <div className="mode-box"><span>{locale === "ko" ? "현재 모드" : "Current mode"}</span><strong>{mode}</strong>{(mode === "결합 검색" || mode === "Combined search") && <small>{locale === "ko" ? "이미지와 텍스트 조건을 함께 반영합니다." : "Uses both image and text conditions."}</small>}</div>
            </div>
            {error && <div className="form-error" role="alert"><span>{error}</span>{retryRequest && <button type="button" className="text-button" onClick={() => void runSearch(retryRequest)}>{locale === "ko" ? "다시 시도" : "Try again"}</button>}</div>}
            <div className="search-actions"><button className="primary-button" type="submit" form="asset-search-form" disabled={isLoading}>{isLoading ? (locale === "ko" ? "검색 중…" : "Searching…") : (locale === "ko" ? "검색하기" : "Search")}</button><button type="button" className="secondary-button" onClick={resetSearch} disabled={isLoading}>{locale === "ko" ? "초기화" : "Reset"}</button><button type="button" className="mobile-filter-button" onClick={() => setMobileFiltersOpen(true)}>{locale === "ko" ? "필터" : "Filters"}{selectedCount > 0 ? ` ${selectedCount}` : ""}</button></div>
          </section>
          {image && <section className="weight-panel" aria-label={copy.imageTuning}><div><h2>{copy.imageTuning}</h2><p>{copy.tuningDescription}</p></div><div className="weight-control"><div className="weight-values"><span>{copy.image} <strong>{imageWeight}%</strong></span><span>{copy.text} <strong>{100 - imageWeight}%</strong></span></div><input name="image-weight" aria-label={locale === "ko" ? "이미지 가중치" : "Image weight"} type="range" min="0" max="100" value={imageWeight} onChange={(event) => setImageWeight(Number(event.target.value))} /><div className="weight-labels"><span>{copy.imageFirst}</span><span>{copy.textFirst}</span></div><p className="weight-summary">{copy.setting}: {copy.image} {imageWeight}% + {copy.text} {100 - imageWeight}%</p></div></section>}
          <section className="results-section" aria-live="polite" aria-busy={isLoading}><div className="results-head"><div><span className="section-label">{locale === "ko" ? "검색 결과" : "Search results"}</span><h2>{isLoading ? (locale === "ko" ? "검색 중…" : "Searching…") : response ? (locale === "ko" ? `상위 검색 결과 ${response.offset === 0 ? response.results.length : `${response.offset + 1}–${response.offset + response.results.length}`}개` : `Top search results ${response.offset === 0 ? response.results.length : `${response.offset + 1}–${response.offset + response.results.length}`}`) : hasNoResultResponse ? (locale === "ko" ? "검색 결과 없음" : "No results") : (locale === "ko" ? "검색을 시작해 주세요" : "Start a search")}</h2>{response && <p className="result-summary">{locale === "ko" ? `전체 후보 ${response.totalCount.toLocaleString()}개 · 상위 ${rankedResultCount}개까지 조회 가능` : `${response.totalCount.toLocaleString()} total candidates · browse the top ${rankedResultCount}`}</p>}</div></div>
            {activeFilterValues.length > 0 && <div className="active-filters">{activeFilterValues.map(({ key, value }) => <span key={`${key}-${value}`}>{filterLabels[locale][key]}: {displayValue(value, locale)}</span>)}<button className="text-button" onClick={resetFilters}>{locale === "ko" ? "모두 지우기" : "Clear all"}</button></div>}
            {isLoading ? <div className="results-grid skeleton-grid">{Array.from({ length: 8 }, (_, index) => <div className="skeleton-card" key={index} />)}</div> : response?.results.length ? <><div className="results-grid">{response.results.map((asset) => <ResultCard key={asset.assetId} asset={asset} locale={locale} onDetails={setSelectedAsset} onSimilar={searchSimilar} />)}</div><nav className="pagination" aria-label={locale === "ko" ? "검색 결과 페이지" : "Search result pages"}><button type="button" className="secondary-button" disabled={!canGoPrevious} onClick={() => response && void runSearch({ offset: Math.max(0, response.offset - resultPageSize) })}>{copy.previous}</button><span>{response.offset + 1}–{response.offset + response.results.length} / {rankedResultCount}</span><button type="button" className="secondary-button" disabled={!canGoNext} onClick={() => response && void runSearch({ offset: response.offset + response.results.length })}>{copy.next}</button></nav></> : <div className="empty-state"><strong>{hasSearched ? copy.noResults : copy.empty}</strong><p>{hasSearched ? copy.noResultsHelp : copy.emptyHelp}</p>{hasSearched && <button type="button" className="secondary-button" onClick={resetFilters}>{copy.resetFilters}</button>}</div>}
          </section>
        </section>
      </div>
      {isMobileFiltersOpen && <div className="mobile-filter-backdrop" onMouseDown={() => setMobileFiltersOpen(false)}><div className="mobile-filter-sheet" role="dialog" aria-modal="true" aria-label={copy.filter} onMouseDown={(event) => event.stopPropagation()}><div className="sheet-top"><h2>{copy.filter}</h2><button type="button" className="icon-button" aria-label={copy.closeFilters} onClick={() => setMobileFiltersOpen(false)}>×</button></div><FilterPanel key={`mobile-${filterCollapseVersion}`} catalog={filterCatalog} collapseVersion={filterCollapseVersion} error={hasFilterCatalogError} filters={filters} isLoading={isFilterCatalogLoading} locale={locale} onChange={updateFilters} onReload={() => void reloadFilterCatalog()} onReset={resetFilters} compact /><button type="button" className="primary-button mobile-apply" onClick={() => setMobileFiltersOpen(false)}>{copy.applyFilters}</button></div></div>}
      <AssetDetail asset={selectedAsset} locale={locale} onClose={() => setSelectedAsset(null)} onSimilar={searchSimilar} />
    </main>
  );
}
