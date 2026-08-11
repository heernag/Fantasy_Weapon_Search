import type { SearchFilters } from "@/src/types/asset";

type FilterKey = keyof SearchFilters;

const groups: Array<{ key: FilterKey; label: string; values: string[] }> = [
  { key: "weaponType", label: "무기 종류", values: ["검", "도끼", "창", "활", "지팡이", "방패"] },
  { key: "colors", label: "주요 색상", values: ["금색", "은색", "검은색", "붉은색", "푸른색", "녹색"] },
  { key: "elements", label: "속성", values: ["불", "얼음", "번개", "독", "암흑", "신성", "무속성"] },
  { key: "worldStyles", label: "세계관 스타일", values: ["중세", "고딕", "엘프", "오크", "마법"] },
  { key: "forms", label: "형태", values: ["한손", "양손", "장검", "단검", "곡선형", "대형"] },
  { key: "rarity", label: "희귀도", values: ["일반", "희귀", "전설"] },
  { key: "visualStyle", label: "시각 스타일", values: ["픽셀아트", "일러스트", "아이콘"] }
];

export function FilterPanel({ filters, onChange, onReset, compact = false }: { filters: SearchFilters; onChange: (key: FilterKey, value: string) => void; onReset: () => void; compact?: boolean }) {
  const count = Object.values(filters).flat().length;
  return (
    <aside className={`filter-panel ${compact ? "filter-panel-compact" : ""}`} aria-label="속성 필터">
      <div className="filter-heading"><div><h2>속성 필터</h2><span>{count}개 선택됨</span></div><button className="text-button" onClick={onReset}>초기화</button></div>
      <div className="filter-groups">
        {groups.map((group) => (
          <fieldset key={group.key} className="filter-group">
            <legend>{group.label}</legend>
            <div className="filter-options">
              {group.values.map((value) => {
                const selected = (filters[group.key] as string[]).includes(value);
                return <label key={value} className={selected ? "filter-option is-selected" : "filter-option"}><input type="checkbox" checked={selected} onChange={() => onChange(group.key, value)} /><span>{value}</span></label>;
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </aside>
  );
}
