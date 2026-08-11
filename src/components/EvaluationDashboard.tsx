const modelRows = [
  { name: "CLIP 벡터 검색", recall1: 42.1, recall5: 67.3, mrr: 52, match: 61.2, tone: "muted" },
  { name: "이미지+텍스트 가중합", recall1: 49.8, recall5: 75.9, mrr: 63, match: 76.5, tone: "violet" },
  { name: "가중합 + 메타데이터 재정렬", recall1: 58.6, recall5: 82.4, mrr: 71, match: 88, tone: "blue" }
];

const modes = [{ label: "텍스트", value: 78 }, { label: "이미지", value: 81 }, { label: "이미지+텍스트", value: 88 }];

export function EvaluationDashboard() {
  return (
    <section className="evaluation-page" aria-labelledby="evaluation-title">
      <header className="evaluation-header"><div><span className="section-label">평가 목데이터</span><h1 id="evaluation-title">검색 품질 평가</h1><p>기준 검색과 멀티모달·메타데이터 재정렬 적용 결과를 비교합니다.</p></div><span className="demo-badge">발표용 예시 수치</span></header>
      <div className="evaluation-kpis">
        {[ ["Recall@5", "82.4%", "상위 5개 내 정답 비율"], ["MRR", "0.71", "첫 정답의 평균 순위"], ["조건 만족률@5", "88.0%", "색상·속성 조건 충족"], ["평균 응답 시간", "142ms", "로컬 검색 기준"] ].map(([label, value, detail]) => <div className="kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>)}
      </div>
      <div className="chart-layout">
        <section className="chart-panel model-table"><div className="panel-heading"><div><h2>모델별 지표 비교</h2><p>개선 요소가 검색 품질에 미치는 영향</p></div><span className="demo-badge">평가 목데이터</span></div><div className="metric-header"><span>모델</span><span>R@1</span><span>R@5</span><span>MRR</span><span>조건</span></div>{modelRows.map((row) => <div className="metric-row" key={row.name}><strong>{row.name}</strong><span>{row.recall1}%</span><span>{row.recall5}%</span><span>{(row.mrr / 100).toFixed(2)}</span><span className={`metric-pill ${row.tone}`}>{row.match}%</span></div>)}</section>
        <section className="chart-panel"><div className="panel-heading"><div><h2>검색 방식별 Recall@5</h2><p>결합 검색이 가장 높은 재현율을 보입니다.</p></div><span className="demo-badge">평가 목데이터</span></div><div className="mode-chart">{modes.map((mode) => <div className="mode-bar" key={mode.label}><div className="bar-top"><span>{mode.label}</span><strong>{mode.value}%</strong></div><div className="bar-track"><span style={{ width: `${mode.value}%` }} /></div></div>)}</div></section>
      </div>
      <div className="chart-layout lower-layout"><section className="chart-panel"><div className="panel-heading"><div><h2>필터 재정렬 효과</h2><p>후보 수를 줄이면서 조건 만족도를 높입니다.</p></div></div><div className="before-after"><div><span>필터 적용 전</span><strong>100개</strong><small>조건 만족률 68%</small></div><span className="arrow">→</span><div className="highlight"><span>필터 적용 후</span><strong>24개</strong><small>조건 만족률 91%</small></div></div></section><section className="chart-panel"><div className="panel-heading"><div><h2>사례 확인</h2><p>발표에서 품질과 한계를 함께 설명합니다.</p></div></div><div className="case-grid"><div className="case success"><strong>성공 사례</strong><p>검 이미지 + “황금색이며 불 속성으로”</p><span>형태 유지와 속성 변경이 함께 반영됨</span></div><div className="case attention"><strong>개선이 필요한 사례</strong><p>매우 추상적인 속성 표현</p><span>태그 정규화와 평가 데이터 보강 필요</span></div></div></section></div>
      <p className="evaluation-note">텍스트·이미지·결합 질의별 100개 평가 질의를 기준으로 한 발표용 예시 수치입니다. 실제 데이터·모델 연결 후 재계산이 필요합니다.</p>
    </section>
  );
}
