"use client";

import { useState } from "react";

export type Failure = {
  query: string;
  top_results: { asset_id: string; score: number }[];
  relevant_asset_ids: string[];
};

export type Group = Record<string, { query_count: number; recall_at_10?: number; mrr?: number; "Recall@10"?: number; MRR?: number }>;

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

function normalizedMetrics(value: Group[string]) {
  return {
    recallAt10: value.recall_at_10 ?? value["Recall@10"] ?? 0,
    mrr: value.mrr ?? value.MRR ?? 0,
  };
}

type RankedMetric = {
  key: string;
  value: Group[string];
  recallAt10: number;
  mrr: number;
  priority: number;
};

function rankImprovementTargets(data: Group): RankedMetric[] {
  return Object.entries(data)
    .map(([key, value]) => {
      const { recallAt10, mrr } = normalizedMetrics(value);
      // 낮은 검색 품질을 우선하되, 표본이 너무 적은 항목이 과도하게 앞서지 않게 합니다.
      const evidence = Math.min(1, value.query_count / 5);
      const quality = recallAt10 * 0.7 + mrr * 0.3;
      return { key, value, recallAt10, mrr, priority: (1 - quality) * (0.45 + evidence * 0.55) };
    })
    .toSorted((left, right) => right.priority - left.priority || right.value.query_count - left.value.query_count || left.key.localeCompare(right.key));
}

function ChartLegend() {
  return <p className="chart-legend" aria-label="그래프 범례"><span><i className="legend-dot recall" aria-hidden="true" />Recall@10</span><span><i className="legend-dot mrr" aria-hidden="true" />MRR</span></p>;
}

export function MetricBarChart({ title, data, labelFor = (key) => key }: { title: string; data: Group; labelFor?: (key: string) => string }) {
  const rows = rankImprovementTargets(data);
  return <section className="chart-card" aria-labelledby={`${title}-heading`}>
    <div className="chart-heading"><div><h2 id={`${title}-heading`}>{title}</h2><p className="chart-description">개선 우선순위 순입니다. Recall@10·MRR이 낮고 표본 수가 충분한 항목을 먼저 보여줍니다.</p></div><ChartLegend /></div>
    {rows.length === 0 ? <p className="empty-state">표시할 평가 데이터가 없습니다.</p> : <div className="metric-chart" role="img" aria-label={`${title} Recall@10 및 MRR 비교 그래프`}>
      <div className="metric-axis" aria-hidden="true"><span>0%</span><span>100%</span></div>
      {rows.map((row, index) => {
        return <div className="metric" key={row.key}>
          <div className="metric-copy"><div><strong>{labelFor(row.key)}</strong><em>개선 우선 {index + 1}</em></div><span>{row.value.query_count}개 쿼리</span></div>
          <div className="metric-values"><span>R@10 {percent(row.recallAt10)}</span><span>MRR {percent(row.mrr)}</span></div>
          <div className="metric-tracks" aria-hidden="true"><span className="metric-track"><i className="metric-fill recall" style={{ width: `${row.recallAt10 * 100}%` }} /></span><span className="metric-track"><i className="metric-fill mrr" style={{ width: `${row.mrr * 100}%` }} /></span></div>
        </div>;
      })}
    </div>}
  </section>;
}

export function TrendChart({ data }: { data: { date: string; recall_at_10: number; mrr: number }[] }) {
  return <section className="chart-card" aria-labelledby="trend-heading">
    <div className="chart-heading"><h2 id="trend-heading">Recall@10 · MRR 추이</h2><ChartLegend /></div>
    {data.length === 0 ? <p className="empty-state">누적 평가 이력이 아직 없습니다.</p> : <div className="trend-chart" role="img" aria-label="날짜별 Recall@10 및 MRR 추이 그래프">
      <div className="trend-axis" aria-hidden="true"><span>100%</span><span>50%</span><span>0%</span></div>
      <div className="trend-bars">{data.map((row, index) => <div className="trend-group" key={`${row.date}-${index}`}>
        <div className="trend-columns" aria-hidden="true"><i className="trend-bar recall" style={{ height: `${row.recall_at_10 * 100}%` }} /><i className="trend-bar mrr" style={{ height: `${row.mrr * 100}%` }} /></div>
        <span className="trend-label">{row.date}</span><span className="trend-value">R@10 {percent(row.recall_at_10)} · MRR {percent(row.mrr)}</span>
      </div>)}</div>
    </div>}
  </section>;
}

export type SearchMode = {
  key: "image" | "text" | "multimodal";
  label: string;
  image_weight: number | null;
  text_weight: number | null;
  query_count: number | null;
  recall: Record<string, number | null>;
  metrics: { map: number | null; recall_at_10: number | null; mrr: number | null; ndcg_at_10: number | null };
};

const MODE_STYLE: Record<SearchMode["key"], { color: string; dash?: string }> = {
  image: { color: "#258ec4" },
  text: { color: "#23aaa5", dash: "6 5" },
  multimodal: { color: "#4b579d" },
};

const metricPercent = (value: number | null | undefined) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;

function ModeLegend({ modes }: { modes: SearchMode[] }) {
  return <p className="chart-legend" aria-label="검색 모드 범례">{modes.map((mode) => <span key={mode.key}><i className={`legend-dot mode-${mode.key}`} aria-hidden="true" />{mode.label}</span>)}</p>;
}

export function SearchModeCharts({ modes }: { modes: SearchMode[] }) {
  const usableModes = modes.filter((mode) => Object.values(mode.recall).some((value) => typeof value === "number"));
  const [tooltip, setTooltip] = useState<{ x: number; y: number; title: string; detail: string } | null>(null);
  const recallKeys = ["1", "5", "10"];
  const chartWidth = 620;
  const chartHeight = 340;
  const plot = { left: 62, top: 22, width: 530, height: 246 };
  const xAt = (index: number) => plot.left + (plot.width / (recallKeys.length - 1)) * index;
  const yAt = (value: number) => plot.top + (1 - value) * plot.height;
  const barMetrics = [
    { key: "map", label: "mAP" },
    { key: "recall_at_10", label: "Recall@10" },
    { key: "mrr", label: "MRR" },
    { key: "ndcg_at_10", label: "nDCG@10" },
  ] as const;

  if (usableModes.length !== 3) return <section className="chart-card"><h2>검색 방식별 성능 비교</h2><p className="empty-state">세 검색 모드의 평가 결과를 준비하는 중입니다.</p></section>;

  return <section className="mode-performance" aria-labelledby="mode-performance-heading">
    <div className="mode-performance-heading"><div><p className="eyebrow">동일한 멀티모달 검증 데이터 기준</p><h2 id="mode-performance-heading">검색 방식별 성능 비교</h2><p>이미지 전용·텍스트 전용·이미지와 텍스트를 함께 쓰는 검색의 품질을 비교합니다. 그래프의 점 또는 막대에 마우스를 올리면 정확한 수치를 볼 수 있습니다.</p></div></div>
    <div className="mode-chart-grid">
      <section className="chart-card interactive-card" aria-labelledby="recall-curve-heading"><div className="chart-heading"><div><h2 id="recall-curve-heading">Recall@K 곡선</h2><p>상위 K개 안에서 정답을 찾는 비율입니다. 높을수록 좋습니다.</p></div></div>
        <div className="interactive-chart">{tooltip?.title.startsWith("Recall") && <div className="chart-tooltip" style={{ left: `${tooltip.x}%`, top: `${tooltip.y}%` }}><strong>{tooltip.title}</strong><span>{tooltip.detail}</span></div>}
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="검색 방식별 Recall at K 비교 선 그래프">
            {[0, .25, .5, .75, 1].map((value) => <g key={value}><line x1={plot.left} x2={plot.left + plot.width} y1={yAt(value)} y2={yAt(value)} className="chart-grid-line" /><text x={plot.left - 12} y={yAt(value) + 4} textAnchor="end" className="chart-axis-text">{Math.round(value * 100)}%</text></g>)}
            {recallKeys.map((key, index) => <text key={key} x={xAt(index)} y={plot.top + plot.height + 28} textAnchor="middle" className="chart-axis-text">K={key}</text>)}
            {usableModes.map((mode) => { const points = recallKeys.map((key, index) => `${xAt(index)},${yAt(mode.recall[key] ?? 0)}`).join(" "); return <g key={mode.key}><polyline points={points} fill="none" stroke={MODE_STYLE[mode.key].color} strokeWidth="3" strokeDasharray={MODE_STYLE[mode.key].dash} />{recallKeys.map((key, index) => { const value = mode.recall[key] ?? 0; return <circle key={key} className="chart-marker" cx={xAt(index)} cy={yAt(value)} r="5" fill="#fff" stroke={MODE_STYLE[mode.key].color} strokeWidth="3" tabIndex={0} aria-label={`${mode.label} Recall at ${key}, ${metricPercent(value)}`} onMouseEnter={() => setTooltip({ x: (xAt(index) / chartWidth) * 100, y: (yAt(value) / chartHeight) * 100, title: `Recall@${key}`, detail: `${mode.label} ${metricPercent(value)}` })} onFocus={() => setTooltip({ x: (xAt(index) / chartWidth) * 100, y: (yAt(value) / chartHeight) * 100, title: `Recall@${key}`, detail: `${mode.label} ${metricPercent(value)}` })} onMouseLeave={() => setTooltip(null)} onBlur={() => setTooltip(null)} />; })}</g>; })}
          </svg>
        </div><ModeLegend modes={usableModes} />
      </section>
      <section className="chart-card interactive-card" aria-labelledby="metric-comparison-heading"><div className="chart-heading"><div><h2 id="metric-comparison-heading">핵심 지표 비교</h2><p>mAP, Recall@10, MRR, nDCG@10 기준으로 세 검색 방식을 비교합니다.</p></div></div>
        <div className="interactive-chart">{tooltip?.title.startsWith("metric") && <div className="chart-tooltip" style={{ left: `${tooltip.x}%`, top: `${tooltip.y}%` }}><strong>{tooltip.title.replace("metric:", "")}</strong><span>{tooltip.detail}</span></div>}
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="검색 방식별 핵심 지표 비교 막대 그래프">
            {[0, .25, .5, .75, 1].map((value) => <g key={value}><line x1={plot.left} x2={plot.left + plot.width} y1={yAt(value)} y2={yAt(value)} className="chart-grid-line" /><text x={plot.left - 12} y={yAt(value) + 4} textAnchor="end" className="chart-axis-text">{value.toFixed(2)}</text></g>)}
            {barMetrics.map((metric, index) => { const groupX = plot.left + (plot.width / barMetrics.length) * index + 16; return <g key={metric.key}>{usableModes.map((mode, modeIndex) => { const value = mode.metrics[metric.key] ?? 0; const barWidth = 28; const x = groupX + modeIndex * 33; const y = yAt(value); return <rect key={mode.key} className="chart-bar" x={x} y={y} width={barWidth} height={plot.top + plot.height - y} rx="3" fill={MODE_STYLE[mode.key].color} tabIndex={0} aria-label={`${metric.label}, ${mode.label}, ${metricPercent(value)}`} onMouseEnter={() => setTooltip({ x: ((x + barWidth / 2) / chartWidth) * 100, y: (y / chartHeight) * 100, title: `metric:${metric.label}`, detail: `${mode.label} ${metricPercent(value)}` })} onFocus={() => setTooltip({ x: ((x + barWidth / 2) / chartWidth) * 100, y: (y / chartHeight) * 100, title: `metric:${metric.label}`, detail: `${mode.label} ${metricPercent(value)}` })} onMouseLeave={() => setTooltip(null)} onBlur={() => setTooltip(null)} />; })}<text x={groupX + 42} y={plot.top + plot.height + 28} textAnchor="middle" className="chart-axis-text">{metric.label}</text></g>; })}
          </svg>
        </div><ModeLegend modes={usableModes} />
      </section>
    </div>
  </section>;
}

export function FailureComparisonModal({ item, onClose }: { item: Failure | null; onClose: () => void }) {
  if (!item) return null;
  return <div className="modal" role="presentation" onMouseDown={onClose}>
    <section className="modal-content" role="dialog" aria-modal="true" aria-labelledby="failure-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
      <button className="modal-close" type="button" aria-label="닫기" onClick={onClose}>×</button><h2 id="failure-dialog-title">실패 쿼리 비교</h2><p className="failure-query">{item.query}</p>
      <h3>기대 정답</h3><p>{item.relevant_asset_ids.join(", ") || "등록된 정답이 없습니다."}</p><h3>상위 검색 결과</h3>
      {item.top_results.length ? <ol className="result-list">{item.top_results.map((result) => <li key={result.asset_id}><span>{result.asset_id}</span><strong>{result.score.toFixed(4)}</strong></li>)}</ol> : <p>검색 결과가 없습니다.</p>}
    </section>
  </div>;
}
