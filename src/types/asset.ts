export type WeaponType = "검" | "도끼" | "창" | "활" | "지팡이" | "방패";
export type Rarity = "일반" | "희귀" | "전설";
export type VisualStyle = "픽셀아트" | "일러스트" | "아이콘";

export type SearchFilters = {
  weaponType: WeaponType[];
  colors: string[];
  elements: string[];
  worldStyles: string[];
  forms: string[];
  rarity: Rarity[];
  visualStyle: VisualStyle[];
};

export type Asset = {
  assetId: string;
  title: string;
  descriptionKo: string;
  weaponType: WeaponType;
  colors: string[];
  elements: string[];
  worldStyles: string[];
  forms: string[];
  rarity: Rarity;
  visualStyle: VisualStyle;
  similarity: number;
  vectorSimilarity: number;
  metadataMatch: number;
  source: string;
  creator: string;
  sourceUrl: string;
  license: string;
  licenseCheckedAt: string;
  matchReasons: string[];
  tone: "violet" | "blue" | "orange" | "green" | "slate" | "red";
};

export type SearchRequest = {
  query: string;
  imageName?: string;
  imageWeight: number;
  filters: SearchFilters;
  sort: "score" | "similarity" | "match" | "title";
};

export type SearchResponse = {
  results: Asset[];
  totalCount: number;
  averageSimilarity: number;
  conditionMatchRate: number;
  elapsedMs: number;
};

export const emptyFilters: SearchFilters = {
  weaponType: [],
  colors: [],
  elements: [],
  worldStyles: [],
  forms: [],
  rarity: [],
  visualStyle: []
};
