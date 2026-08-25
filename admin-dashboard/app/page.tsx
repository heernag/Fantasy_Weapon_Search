"use client";

import { useEffect, useState } from "react";
import { FailureComparisonModal, MetricBarChart, SearchModeCharts, TrendChart, type Failure, type Group, type SearchMode } from "./components";

type Metrics = {
  failed_queries: Failure[];
  trend: { date: string; recall_at_10: number; mrr: number }[];
  by_query_type: Group;
  by_dimension: Record<string, Group>;
  quality_sets: { dataset: string; query_count: number | null; map: number | null; recall_at_10: number | null; mrr: number | null; ndcg: number | null }[];
  zero_result_rate: number | null;
  average_latency_ms: number | null;
  p95_latency_ms: number | null;
  mode_comparison: SearchMode[];
};

const queryTypeLabels: Record<string, string> = { color_change: "색상 변경", element_change: "속성 변경", material_change: "재질 변경", style_change: "시각 스타일 변경" };
const dimensionLabels: Record<string, string> = { weapon_category: "무기 종류", primary_color: "주요 색상", elements: "속성" };
const percent = (value: number | null | undefined) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;
const milliseconds = (value: number | null | undefined) => value == null ? "—" : `${value < 10 ? value.toFixed(1) : Math.round(value)}ms`;

export default function EvaluationDashboard() {
  const [data, setData] = useState<Metrics | null>(null);
  const [selected, setSelected] = useState<Failure | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/backend/evaluation/metrics", { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(response.status))
      .then(setData)
      .catch((reason) => { if (reason?.name !== "AbortError") setError("평가 데이터를 불러오지 못했습니다. 백엔드 서버와 결과 파일을 확인해 주세요."); });
    return () => controller.abort();
  }, []);

  const validation = data?.quality_sets.find((item) => item.dataset === "multimodal_validation");

  return <main>
    <header><span translate="no">Fantasy Weapon Search</span><b>ADMIN</b></header>
    <div className="page">
      <div className="dashboard-title"><p className="eyebrow">검색 품질 · 운영 성능</p><h1>검색 성능 평가 대시보드</h1><p>실제 평가 실행 결과를 바탕으로 검색 품질과 개선이 필요한 영역을 확인합니다.</p></div>
      {error ? <p className="error" role="alert">{error}</p> : !data ? <p aria-live="polite">불러오는 중…</p> : <>
        <section className="dashboard-guide" aria-labelledby="guide-heading">
          <div><h2 id="guide-heading">이 화면을 보는 순서</h2><p>먼저 전체 품질을 확인한 뒤, 검색 방식별 비교로 가장 효과적인 조합을 판단합니다. 이어서 쿼리 유형과 메타데이터별 진단에서 개선 대상을 찾습니다.</p></div>
          <ol><li><strong>전체 품질</strong> — mAP, Recall@10, MRR, nDCG@10</li><li><strong>검색 방식</strong> — 이미지·텍스트·결합 검색 비교</li><li><strong>세부 진단</strong> — 유형·무기·색상·속성별 편차 확인</li></ol>
        </section>

        <section className="evaluation-overview" aria-labelledby="overview-heading">
          <div className="summary-heading"><div><p className="eyebrow">동일한 멀티모달 검증 데이터 기준</p><h2 id="overview-heading">이번 평가의 전체 성적</h2><p>결합 검색에서 선택된 최적 가중치의 실제 측정값입니다.</p></div><span>{validation?.query_count ?? 0}개 쿼리</span></div>
          <div className="summary-grid">
            <article><strong>mAP</strong><b>{percent(validation?.map)}</b><span>관련 결과의 전체 순위 품질</span></article>
            <article><strong>Recall@10</strong><b>{percent(validation?.recall_at_10)}</b><span>상위 10개 안에 정답이 포함된 비율</span></article>
            <article><strong>MRR</strong><b>{percent(validation?.mrr)}</b><span>정답이 앞 순위에 있을수록 높아짐</span></article>
            <article><strong>nDCG@10</strong><b>{percent(validation?.ndcg)}</b><span>정답의 순위까지 반영한 품질</span></article>
            <article><strong>무결과율</strong><b>{percent(data.zero_result_rate)}</b><span>검색 결과가 0개인 비율 · 낮을수록 좋음</span></article>
            <article><strong>응답 시간</strong><b>{milliseconds(data.average_latency_ms)}</b><span>평균 · P95 {milliseconds(data.p95_latency_ms)}</span></article>
          </div>
          <SearchModeCharts modes={data.mode_comparison ?? []} />
        </section>

        <section className="diagnostics-section" aria-labelledby="diagnostics-heading">
          <div className="diagnostics-heading"><div><p className="eyebrow">개선 대상 탐색</p><h2 id="diagnostics-heading">세부 성능 진단</h2><p>같은 결합 검색 결과를 쿼리 조건과 메타데이터 기준으로 나눠 약한 영역을 찾습니다.</p></div></div>
          <MetricBarChart title="쿼리 유형별 성능" data={data.by_query_type} labelFor={(key) => queryTypeLabels[key] ?? key} />
          {Object.entries(data.by_dimension).map(([name, group]) => <MetricBarChart key={name} title={`${dimensionLabels[name] ?? name}별 성능`} data={group} />)}
          <TrendChart data={data.trend} />
          {data.failed_queries.length > 0 && <section className="failure-card" aria-labelledby="failures-heading"><h2 id="failures-heading">실패 쿼리</h2><p>항목을 선택하면 기대 정답과 실제 상위 검색 결과를 비교할 수 있습니다.</p><ul className="failure-list">{data.failed_queries.map((item, index) => <li key={`${item.query}-${index}`}><button type="button" onClick={() => setSelected(item)}>{item.query}</button></li>)}</ul></section>}
        </section>
      </>}
      <FailureComparisonModal item={selected} onClose={() => setSelected(null)} />
    </div>
  </main>;
}
