import { useState } from "react";
import { approvedOptionsFor, approvedSubcategoriesFor, visibleFilterGroups } from "@/src/lib/filterConfig";
import { displayValue, filterLabels, type Locale } from "@/src/lib/labels";
import { listFilterKeys, type FilterCatalog, type FilterKey, type SearchFilters } from "@/src/types/asset";

const longGroups = new Set<FilterKey>(["primary_color", "shape_tags"]);
const count = (filters: SearchFilters) => Object.values(filters).reduce((total, value) => total + (Array.isArray(value) ? value.length : Number(Boolean(value))), 0);
const categoryIcons: Record<string, string> = { sword: "⚔", dagger: "🗡", axe: "🪓", bow: "🏹", shield: "🛡", staff: "✦", gun: "⌖", spear: "↟", scythe: "☾", mace: "✹", hammer: "🔨", chakram: "◌", shuriken: "✥", crossbow: "╫", arrow: "➶" };
const groupIcons: Partial<Record<FilterKey, string>> = { category: "⚔", subcategory: "⌘", grade: "✦", primary_color: "●", elements: "⚡", shape_tags: "◇", materials: "◈", visual_style: "▣" };
const elementIcons: Record<string, string> = { dark: "◐", fire: "🔥", holy: "✦", ice: "❄", lightning: "⚡", nature: "🌿", poison: "☠", water: "💧", wind: "〰" };
const materialIcons: Record<string, string> = { bone: "⊹", bronze: "●", chain: "⌇", cloth: "▧", crystal: "◇", gold: "✦", leather: "◒", obsidian: "◆", silver: "○", steel: "▰", stone: "⬟", wood: "≋" };
const gradeIcons: Record<string, string> = { common: "◇", legendary: "✦" };
const shapeIcons: Record<string, string> = { one_handed: "Ⅰ", bladed: "◢", straight_blade: "│", two_handed: "Ⅱ", symmetrical: "◈", pointed_bottom: "▽", rounded_edges: "◯", shield_shaped: "⬟", pointed_top: "△", ornate: "✧", double_edged: "⇋", broad_blade: "▰", long_blade: "▯", dagger: "◢", single_blade: "◿", longsword: "┃", round: "○", curved_blade: "◜", enchanted: "✦", long_handle: "╏", compact_blade: "▪", crystal_detail: "◇", glowing: "☼", short_blade: "▭", layered: "≡", double_blade: "✣" };
const visualStyleIcons: Record<string, string> = { pixel_art: "▦", illustration: "✎", rendered_icon: "▣" };

function OptionAdornment({ category, group, value }: { category: string | null; group: FilterKey; value: string }) {
  if (group === "category") return <span className="filter-option-icon" aria-hidden="true">{categoryIcons[value] ?? "◇"}</span>;
  if (group === "subcategory") return <span className="filter-option-icon" aria-hidden="true">{categoryIcons[category ?? ""] ?? "◇"}</span>;
  if (group === "grade") return <span className="filter-option-icon" aria-hidden="true">{gradeIcons[value] ?? "◇"}</span>;
  if (group === "elements") return <span className="filter-option-icon" aria-hidden="true">{elementIcons[value] ?? "✧"}</span>;
  if (group === "shape_tags") return <span className="filter-option-icon" aria-hidden="true">{shapeIcons[value] ?? "◇"}</span>;
  if (group === "materials") return <span className="filter-option-icon" aria-hidden="true">{materialIcons[value] ?? "◈"}</span>;
  if (group === "visual_style") return <span className="filter-option-icon" aria-hidden="true">{visualStyleIcons[value] ?? "▣"}</span>;
  if (group === "primary_color") return <i className={`color-swatch color-${value}`} aria-hidden="true" />;
  return null;
}

function FilterGroupIcon({ group }: { group: FilterKey }) {
  if (group === "elements") return <svg className="filter-group-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m13.2 2.8-8 10.3h5.4l-.8 8.1 9-11.5h-5.5l-.1-6.9Z" /></svg>;
  if (group === "materials") return <svg className="filter-group-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.2 7 4v8.2l-7 4-7-4V7.2l7-4Z" /><path d="m5 7.2 7 4 7-4M12 11.2v8.2" /></svg>;
  return <i className="filter-group-icon" aria-hidden="true">{groupIcons[group] ?? "◇"}</i>;
}

type FilterPanelProps = {
  catalog: FilterCatalog | null;
  collapseVersion: number;
  error: boolean;
  filters: SearchFilters;
  isLoading: boolean;
  locale: Locale;
  compact?: boolean;
  onChange: (key: FilterKey, value: string) => void;
  onReload: () => void;
  onReset: () => void;
};

export function FilterPanel({ catalog, collapseVersion, error, filters, isLoading, locale, onChange, onReload, onReset, compact = false }: FilterPanelProps) {
  const selectedCount = count(filters);
  const [expandedGroups, setExpandedGroups] = useState<Set<FilterKey>>(() => collapseVersion > 0 ? new Set() : new Set(filters.category ? ["category", "subcategory"] : ["category"]));
  const options: Array<[FilterKey, ReturnType<typeof approvedOptionsFor>]> = visibleFilterGroups.map((key) => [key, approvedOptionsFor(key)]);
  if (filters.category) options.splice(1, 0, ["subcategory", approvedSubcategoriesFor(filters.category)]);
  const applyChange = (key: FilterKey, value: string) => {
    if (key === "category") setExpandedGroups((current) => new Set([...current, "subcategory"]));
    onChange(key, value);
  };

  return <aside className={`filter-panel ${compact ? "filter-panel-compact" : ""}`} aria-label={locale === "ko" ? "속성 필터" : "Attribute filters"} aria-busy={isLoading}>
    <div className="filter-heading"><div><h2>{locale === "ko" ? "속성 필터" : "Filters"}</h2><span>{locale === "ko" ? `${selectedCount}개 선택됨` : `${selectedCount} selected`}</span></div><button type="button" className="text-button" onClick={onReset} disabled={selectedCount === 0}>{locale === "ko" ? "초기화" : "Reset"}</button></div>
    {!catalog && !error && <p className="filter-status" role="status">{locale === "ko" ? "필터를 불러오는 중…" : "Loading filters…"}</p>}
    {!catalog && error && <div className="filter-status filter-status-error" role="alert"><p>{locale === "ko" ? "필터를 불러오지 못했습니다." : "Could not load filters."}</p><button type="button" className="text-button" onClick={onReload}>{locale === "ko" ? "다시 시도" : "Try again"}</button></div>}
    {catalog && <div className="filter-groups">{options.map(([key, values]) => {
      if (key === "subcategory" && values.length === 0) return null;
      const isList = (listFilterKeys as readonly string[]).includes(key);
      const selected = filters[key];
      const selectedValues = Array.isArray(selected) ? selected : selected ? [selected] : [];
      const counts = new Map((catalog?.[key] ?? []).map(({ value, count: optionCount }) => [value, optionCount]));
      const selectedOptions = values.filter(({ value }) => selectedValues.includes(value));
      const visibleValues = selectedOptions.length === values.length ? values : [...selectedOptions, ...values.filter(({ value }) => !selectedValues.includes(value))];
      return <details key={key} className={`filter-group filter-group-${key} ${longGroups.has(key) ? "filter-group-long" : ""}`} open={expandedGroups.has(key)} onToggle={(event) => { const isOpen = event.currentTarget.open; setExpandedGroups((current) => { const next = new Set(current); if (isOpen) next.add(key); else next.delete(key); return next; }); }}><summary><span className="filter-group-title"><FilterGroupIcon group={key} /><span>{filterLabels[locale][key]}</span></span><span className="filter-group-meta">{selectedValues.length > 0 ? selectedValues.length : values.length}</span></summary><div className="filter-options">{visibleValues.map(({ value }) => {
        const active = Array.isArray(selected) ? selected.includes(value) : selected === value;
        return <label key={value} className={active ? "filter-option is-selected" : "filter-option"}><input type={isList ? "checkbox" : "radio"} name={isList ? undefined : key} checked={active} onClick={(event) => { if (!isList && active) { event.preventDefault(); applyChange(key, value); } }} onChange={() => applyChange(key, value)} /><span><OptionAdornment category={filters.category} group={key} value={value} /><b>{displayValue(value, locale)}</b><small>{counts.get(value) ?? 0}</small></span></label>;
      })}</div></details>;
    })}</div>}
  </aside>;
}
