import { categories, filterOptions, subcategoriesByCategory } from "@/src/lib/labels";
import type { FilterKey } from "@/src/types/asset";

/**
 * 공개 검색 화면에 표시할 확정 필터 목록입니다.
 * 백엔드의 추가 메타데이터 값은 검색에 남아 있어도, 여기 등록한 값만
 * UI에 노출합니다. 노출 여부와 표시명은 이 파일과 labels.ts에서 관리합니다.
 */
export const visibleFilterGroups = ["category", "grade", "primary_color", "elements", "shape_tags", "materials", "visual_style"] as const;

type VisibleFilterKey = (typeof visibleFilterGroups)[number];

const visibleOptions = {
  category: categories,
  grade: filterOptions.grade,
  primary_color: filterOptions.primary_color,
  elements: filterOptions.elements,
  shape_tags: filterOptions.shape_tags,
  materials: filterOptions.materials,
  visual_style: filterOptions.visual_style
} satisfies Record<VisibleFilterKey, { value: string; ko: string; en: string }[]>;

export function approvedOptionsFor(key: VisibleFilterKey) {
  return visibleOptions[key];
}

export function approvedSubcategoriesFor(category: string | null) {
  return category ? (subcategoriesByCategory[category] ?? []) : [];
}

export function isVisibleFilterKey(key: FilterKey): key is VisibleFilterKey {
  return (visibleFilterGroups as readonly string[]).includes(key);
}
