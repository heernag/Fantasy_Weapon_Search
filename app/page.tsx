"use client";

import { useEffect, useMemo, useState } from "react";
import { AssetDetail } from "@/src/components/AssetDetail";
import { EvaluationDashboard } from "@/src/components/EvaluationDashboard";
import { FilterPanel } from "@/src/components/FilterPanel";
import { ResultCard } from "@/src/components/ResultCard";
import { mockAssets } from "@/src/data/mockAssets";
import { searchAssets } from "@/src/lib/searchService";
import { emptyFilters, type Asset, type SearchFilters, type SearchRequest, type SearchResponse } from "@/src/types/asset";

type Sort = SearchRequest["sort"];

const defaultQuery = "푸른 마법이 깃든 양손검";
const initialResponse: SearchResponse = { results: mockAssets.slice(0, 12), totalCount: 24, averageSimilarity: 86, conditionMatchRate: 91, elapsedMs: 142 };

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<"search" | "evaluation">("search");
  const [query, setQuery] = useState(defaultQuery);
  const [imageName, setImageName] = useState<string | undefined>();
  const [imageWeight, setImageWeight] = useState(60);
  const [filters, setFilters] = useState<SearchFilters>(emptyFilters);
  const [sort, setSort] = useState<Sort>("score");
  const [response, setResponse] = useState<SearchResponse>(initialResponse);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [isMobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const selectedCount = useMemo(() => Object.values(filters).flat().length, [filters]);
  const mode = imageName && query.trim() ? "결합 검색" : imageName ? "이미지 검색" : "텍스트 검색";
  const activeFilterValues = useMemo(() => Object.values(filters).flat(), [filters]);

  const currentRequest = (): SearchRequest => ({ query, imageName, imageWeight, filters, sort });

  const runSearch = async (next?: Partial<SearchRequest>) => {
    const request = { ...currentRequest(), ...next };
    if (!request.query.trim() && !request.imageName) {
      setError("검색어를 입력하거나 참고 이미지를 선택해 주세요.");
      return;
    }
    setError("");
    setIsLoading(true);
    const nextResponse = await searchAssets(request);
    setResponse(nextResponse);
    setIsLoading(false);
  };

  const updateFilters = (key: keyof SearchFilters, value: string) => {
    const selected = filters[key] as string[];
    const nextFilters = { ...filters, [key]: selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value] } as SearchFilters;
    setFilters(nextFilters);
    void runSearch({ filters: nextFilters });
  };

  const resetFilters = () => {
    setFilters(emptyFilters);
    void runSearch({ filters: emptyFilters });
  };

  const handleFile = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("지원하지 않는 형식입니다. PNG, JPG, WEBP 이미지를 선택해 주세요.");
      return;
    }
    setError("");
    setImageName(file.name);
  };

  const searchSimilar = (asset: Asset) => {
    setImageName(`${asset.title}.png`);
    setSelectedAsset(null);
    void runSearch({ imageName: `${asset.title}.png`, query: "", imageWeight: 82 });
    setImageWeight(82);
    setQuery("");
  };

  const resetSearch = () => {
    setQuery(defaultQuery);
    setImageName(undefined);
    setImageWeight(60);
    setFilters(emptyFilters);
    setSort("score");
    setError("");
    setResponse(initialResponse);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") { setSelectedAsset(null); setMobileFiltersOpen(false); } };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <main id="main-content">
      <header className="app-header">
        <a className="brand" href="#top" aria-label="Arcane Arsenal 홈" translate="no"><span className="brand-mark">A</span><span>Arcane Arsenal</span></a>
        <nav aria-label="주요 탐색"><button className={activeTab === "search" ? "nav-button is-active" : "nav-button"} onClick={() => setActiveTab("search")}>검색</button><button className={activeTab === "evaluation" ? "nav-button is-active" : "nav-button"} onClick={() => setActiveTab("evaluation")}>성능 평가</button></nav>
        <span className="header-demo">목데이터 데모 <span title="실제 검색 API 연결 전 UI 시연용 데이터입니다." aria-label="도움말">ⓘ</span></span>
      </header>
      {activeTab === "evaluation" ? <EvaluationDashboard /> : <div id="top" className="app-layout">
        <div className="desktop-filters"><FilterPanel filters={filters} onChange={updateFilters} onReset={resetFilters} /></div>
        <section className="search-content" aria-labelledby="search-title">
          <header className="search-hero"><span className="section-label">멀티모달 에셋 탐색</span><h1 id="search-title">어떤 무기를 찾고 있나요?</h1><p>텍스트, 참고 이미지, 또는 두 조건을 함께 사용해 보세요.</p></header>
          <section className="search-panel" aria-label="검색 조건">
            <label className="search-input-wrap"><span className="sr-only">자연어 검색</span><span aria-hidden="true">⌕</span><input name="search-query" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runSearch(); }} placeholder="예: 푸른 마법이 깃든 판타지 양손검…" /><button aria-label="검색 실행" onClick={() => void runSearch()}>검색</button></label>
            <div className="example-row"><span>예시</span>{["푸른 마법이 깃든 양손검", "금색 불 속성 무기", "픽셀아트 단검"].map((example) => <button key={example} className="query-chip" onClick={() => { setQuery(example); void runSearch({ query: example }); }}>{example}</button>)}</div>
            <div className="input-row">
              <label className="upload-zone"><input name="reference-image" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleFile(event.target.files?.[0])} /><span className="upload-icon" aria-hidden="true">↑</span><span><strong>{imageName ? imageName : "참고 이미지 추가 (선택)"}</strong><small>{imageName ? "목업 미리보기가 적용되었습니다" : "PNG, JPG, WEBP · 실제 서버 업로드 없음"}</small></span>{imageName && <button type="button" className="clear-image" onClick={(event) => { event.preventDefault(); setImageName(undefined); }}>제거</button>}</label>
              <div className="mode-box"><span>현재 모드</span><strong>{mode}</strong>{mode === "결합 검색" && <small>이미지와 텍스트 조건을 함께 반영합니다.</small>}</div>
            </div>
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="search-actions"><button className="primary-button" onClick={() => void runSearch()} disabled={isLoading}>{isLoading ? "검색 중…" : "검색하기"}</button><button className="secondary-button" onClick={resetSearch}>초기화</button><button className="mobile-filter-button" onClick={() => setMobileFiltersOpen(true)}>필터{selectedCount > 0 ? ` ${selectedCount}` : ""}</button></div>
          </section>
          <section className="weight-panel" aria-label="검색 기준 조절"><div><h2>검색 기준 조절</h2><p>참고 이미지의 형태를 유지할수록 이미지 비중을 높이세요.</p></div><div className="weight-control"><div className="weight-values"><span>이미지 <strong>{imageWeight}%</strong></span><span>텍스트 <strong>{100 - imageWeight}%</strong></span></div><input name="image-weight" aria-label="이미지 가중치" type="range" min="0" max="100" value={imageWeight} onChange={(event) => setImageWeight(Number(event.target.value))} onMouseUp={() => void runSearch()} onTouchEnd={() => void runSearch()} /><div className="weight-labels"><span>이미지 우선 · 형태 유지</span><span>텍스트 우선 · 색상·속성 반영</span></div><p className="weight-summary">현재 설정: 이미지 {imageWeight}% + 텍스트 {100 - imageWeight}% <span title="실제 서비스에서는 임베딩 가중합과 메타데이터 재정렬을 함께 사용합니다.">ⓘ</span></p></div></section>
          <section className="results-section" aria-live="polite"><div className="results-head"><div><span className="section-label">검색 결과</span><h2>{isLoading ? "결과를 정렬하고 있습니다" : `${response.totalCount}개의 에셋을 찾았습니다`}</h2></div><label className="sort-select">정렬 <select value={sort} onChange={(event) => { const nextSort = event.target.value as Sort; setSort(nextSort); void runSearch({ sort: nextSort }); }}><option value="score">종합 점수순</option><option value="similarity">유사도순</option><option value="match">조건 일치순</option><option value="title">이름순</option></select></label></div>
            <div className="result-metrics"><span>평균 유사도 <strong>{response.averageSimilarity}%</strong></span><span>조건 일치율 <strong>{response.conditionMatchRate}%</strong></span><span>응답 시간 <strong>{response.elapsedMs}ms</strong></span><small>목데이터 기준</small></div>
            {activeFilterValues.length > 0 && <div className="active-filters">{activeFilterValues.map((filter) => <span key={filter}>{filter}</span>)}<button className="text-button" onClick={resetFilters}>모두 지우기</button></div>}
            {isLoading ? <div className="results-grid skeleton-grid">{Array.from({ length: 8 }, (_, index) => <div className="skeleton-card" key={index} />)}</div> : response.results.length ? <div className="results-grid">{response.results.map((asset) => <ResultCard key={asset.assetId} asset={asset} onDetails={setSelectedAsset} onSimilar={searchSimilar} />)}</div> : <div className="empty-state"><strong>선택한 조건과 일치하는 에셋이 없습니다.</strong><p>필터를 일부 지우거나 다른 검색어를 사용해 보세요.</p><button className="secondary-button" onClick={resetFilters}>필터 초기화</button></div>}
          </section>
          <footer className="dev-status"><span>개발 상태</span> 프론트엔드 목업 완료 · API 연동 대기 · Docker 통합 예정</footer>
        </section>
      </div>}
      {isMobileFiltersOpen && <div className="mobile-filter-backdrop" onMouseDown={() => setMobileFiltersOpen(false)}><div className="mobile-filter-sheet" role="dialog" aria-modal="true" aria-label="속성 필터" onMouseDown={(event) => event.stopPropagation()}><div className="sheet-top"><h2>속성 필터</h2><button className="icon-button" aria-label="필터 닫기" onClick={() => setMobileFiltersOpen(false)}>×</button></div><FilterPanel filters={filters} onChange={updateFilters} onReset={resetFilters} compact /><button className="primary-button mobile-apply" onClick={() => setMobileFiltersOpen(false)}>필터 적용하기</button></div></div>}
      <AssetDetail asset={selectedAsset} onClose={() => setSelectedAsset(null)} onSimilar={searchSimilar} />
    </main>
  );
}
