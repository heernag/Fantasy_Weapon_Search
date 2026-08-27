import type { FilterKey } from "@/src/types/asset";

export type Locale = "ko" | "en";
type Option = { value: string; ko: string; en: string };
const option = (value: string, ko: string, en?: string): Option => ({ value, ko, en: en ?? value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) });
const rows = (items: string[]) => items.map((item) => { const [value, ko] = item.split(":"); return option(value, ko); });

export const filterLabels: Record<Locale, Record<FilterKey, string>> = {
  ko: { category: "무기 종류", subcategory: "세부 종류", visual_style: "시각 스타일", primary_color: "주요 색상", grade: "희귀도", colors: "색상", elements: "속성", materials: "재질", shape_tags: "형태", style: "세계관 스타일", handedness: "사용 방식" },
  en: { category: "Weapon type", subcategory: "Subtype", visual_style: "Visual style", primary_color: "Primary color", grade: "Rarity", colors: "Colors", elements: "Elements", materials: "Materials", shape_tags: "Shape", style: "World style", handedness: "Handedness" }
};
export const categories = rows(["sword:검", "dagger:단검", "axe:도끼", "bow:활", "shield:방패", "staff:지팡이", "gun:총", "spear:창", "scythe:낫", "mace:메이스", "hammer:망치", "chakram:차크람", "shuriken:표창", "crossbow:석궁", "arrow:화살"]);
const subcategoryRows: Record<string, string[]> = {
  arrow: ["arrow:화살", "standard_arrow:일반 화살", "blunt_arrow:둔두 화살", "broadhead_arrow:광두 화살", "iron_arrow:철 화살", "bolt:석궁 화살", "draining_bolt:흡혈 석궁 화살", "fire_bolt:화염 석궁 화살", "ice_bolt:얼음 석궁 화살", "ice_arrow:얼음 화살", "magic_arrow:마법 화살", "poison_arrow:독 화살", "silver_arrow:은 화살"],
  axe: ["bardiche:바디슈", "battle_axe:전투 도끼", "broad_axe:광두 도끼", "double_axe:양날 도끼", "executioner_axe:처형 도끼", "fantasy_axe:판타지 도끼", "halberd:미늘창", "hand_axe:손도끼", "infantry_axe:보병 도끼", "poleaxe:폴액스", "tomahawk:토마호크", "two_handed_axe:양손 도끼", "war_axe:전쟁 도끼", "winged_axe:날개 도끼"],
  bow: ["demonic_longbow:악마의 장궁", "enchanted_shortbow:마법 단궁", "longbow:장궁", "shortbow:단궁"], chakram: ["chakram:차크람"], crossbow: ["crossbow:석궁", "hand_crossbow:손석궁", "arbalest:대형 석궁"],
  dagger: ["dagger:단검", "curved_dagger:곡도 단검", "dual_dagger:쌍 단검", "katar:카타르", "magic_dagger:마법 단검", "short_dagger:소형 단검", "stiletto:스틸레토", "throwing_dagger:투척 단검"], gun: ["pistol:권총"], hammer: ["war_hammer:워해머", "war_pick:워픽"],
  mace: ["mace:메이스", "standard_mace:일반 메이스", "flail:플레일", "flanged_mace:돌기 메이스", "round_mace:구형 메이스", "skull_mace:해골 메이스", "wooden_club:나무 몽둥이"], scythe: ["war_scythe:워싸이드"],
  shield: ["barbed_shield:가시 방패", "buckler:소방패", "crystal_shield:수정 방패", "dwarven_buckler:드워프 버클러", "elven_buckler:엘프 버클러", "fantasy_shield:판타지 방패", "great_shield:대방패", "heater_shield:히터 방패", "kite_shield:카이트 방패", "magic_shield:마법 방패", "palisade_shield:방책 방패", "round_shield:원형 방패", "spiked_round_shield:가시 원형 방패", "spiked_shield:스파이크 방패", "spiral_shield:나선 방패", "tower_shield:타워 실드", "winged_shield:날개 방패"],
  shuriken: ["four_point_shuriken:사방 수리검", "kunai:쿠나이"], spear: ["spear:창", "standard_spear:일반 창", "crystal_spear:수정 창", "forked_spear:갈퀴 창", "glaive:장도창", "hook_spear:갈고리 창", "javelin:투창", "lance:마상창", "magic_spear:마법 창", "ornate_spear:장식 창", "trident:삼지창", "winged_spear:날개 창"], staff: ["magic_staff:마법 지팡이"],
  sword: ["broadsword:브로드소드", "curved_sword:곡도", "cutlass:커틀러스", "shortsword:소검", "falchion:중검", "longsword:장검", "greatsword:대검", "jagged_sword:톱날 검", "katana:카타나", "rapier:레이피어", "saber:세이버", "scimitar:시미터", "dagger:단검", "short_dagger:소형 단검", "double_sword:쌍검", "triple_sword:삼도류"]
};
export const subcategoriesByCategory = Object.fromEntries(Object.entries(subcategoryRows).map(([category, items]) => [category, rows(items)])) as Record<string, Option[]>;
export const filterOptions: Record<"grade" | "primary_color" | "elements" | "shape_tags" | "materials" | "visual_style", Option[]> = {
  grade: [option("common", "일반", "Common"), option("legendary", "전설", "Legendary")],
  primary_color: rows(["beige:베이지", "black:블랙", "blue:블루", "bronze:브론즈", "brown:브라운", "cyan:시안", "dark_gray:다크 그레이", "red:레드", "gold:골드", "gray:그레이", "green:그린", "indigo:남색", "ivory:아이보리", "lavender:라벤더", "navy:네이비", "olive:올리브", "orange:오렌지", "peach:피치", "pink:핑크", "purple:퍼플", "silver:실버", "tan:황갈색", "teal:청록색", "white:화이트", "yellow:옐로우"]),
  elements: rows(["dark:어둠", "fire:불", "holy:신성", "ice:얼음", "lightning:번개", "nature:자연", "poison:독", "water:물", "wind:바람"]),
  shape_tags: rows(["one_handed:한손", "bladed:날 형태", "straight_blade:직선형 날", "two_handed:양손", "symmetrical:대칭형", "pointed_bottom:뾰족한 하단", "rounded_edges:둥근 테두리", "shield_shaped:방패형", "pointed_top:뾰족한 상단", "ornate:화려함", "double_edged:양날", "broad_blade:넓은 날", "long_blade:긴 날", "dagger:단검", "single_blade:외날", "longsword:롱소드", "round:원형", "curved_blade:곡선형 날", "enchanted:마법 부여", "long_handle:긴 자루", "compact_blade:소형 날", "crystal_detail:수정 장식", "glowing:발광", "short_blade:짧은 날", "layered:레이어드", "double_blade:쌍날"]),
  materials: rows(["bone:뼈", "bronze:청동", "chain:사슬", "cloth:천", "crystal:수정", "gold:금", "leather:가죽", "obsidian:흑요석", "silver:은", "steel:강철", "stone:돌", "wood:나무"]), visual_style: [option("pixel_art", "픽셀아트", "Pixel art"), option("illustration", "일러스트", "Illustration")]
};
const labels = new Map([...categories, ...Object.values(subcategoriesByCategory).flat(), ...Object.values(filterOptions).flat()].map((item) => [item.value, item]));
export function displayValue(value: string | null | undefined, locale: Locale = "ko") { return !value ? (locale === "ko" ? "정보 없음" : "Not available") : labels.get(value)?.[locale] ?? value.replaceAll("_", " "); }
