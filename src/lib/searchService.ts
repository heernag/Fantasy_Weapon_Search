import { mockAssets } from "@/src/data/mockAssets";
import type { Asset, SearchFilters, SearchRequest, SearchResponse } from "@/src/types/asset";

const keywordRules: Array<{ keywords: string[]; field: keyof Pick<Asset, "weaponType" | "colors" | "elements" | "worldStyles" | "forms" | "visualStyle">; values: string[] }> = [
  { keywords: ["검", "소드", "sword"], field: "weaponType", values: ["검"] },
  { keywords: ["도끼", "axe"], field: "weaponType", values: ["도끼"] },
  { keywords: ["창", "spear"], field: "weaponType", values: ["창"] },
  { keywords: ["활", "bow"], field: "weaponType", values: ["활"] },
  { keywords: ["지팡이", "staff"], field: "weaponType", values: ["지팡이"] },
  { keywords: ["방패", "shield"], field: "weaponType", values: ["방패"] },
  { keywords: ["푸른", "파란", "blue"], field: "colors", values: ["푸른색"] },
  { keywords: ["붉은", "빨간", "red"], field: "colors", values: ["붉은색"] },
  { keywords: ["금색", "황금", "gold"], field: "colors", values: ["금색"] },
  { keywords: ["검은", "흑", "black"], field: "colors", values: ["검은색"] },
  { keywords: ["녹색", "초록", "green"], field: "colors", values: ["녹색"] },
  { keywords: ["불", "화염", "fire"], field: "elements", values: ["불"] },
  { keywords: ["얼음", "빙", "ice"], field: "elements", values: ["얼음"] },
  { keywords: ["번개", "lightning"], field: "elements", values: ["번개"] },
  { keywords: ["독", "poison"], field: "elements", values: ["독"] },
  { keywords: ["암흑", "dark"], field: "elements", values: ["암흑"] },
  { keywords: ["신성", "holy"], field: "elements", values: ["신성"] },
  { keywords: ["양손", "two-handed"], field: "forms", values: ["양손"] },
  { keywords: ["단검", "dagger"], field: "forms", values: ["단검"] },
  { keywords: ["픽셀", "pixel"], field: "visualStyle", values: ["픽셀아트"] },
  { keywords: ["마법", "룬", "magic"], field: "worldStyles", values: ["마법"] }
];

const includesAny = (value: string | string[], selected: string[]) =>
  selected.length === 0 || selected.some((item) => (Array.isArray(value) ? value.includes(item) : value === item));

const matchesFilters = (asset: Asset, filters: SearchFilters) =>
  includesAny(asset.weaponType, filters.weaponType) &&
  includesAny(asset.colors, filters.colors) &&
  includesAny(asset.elements, filters.elements) &&
  includesAny(asset.worldStyles, filters.worldStyles) &&
  includesAny(asset.forms, filters.forms) &&
  includesAny(asset.rarity, filters.rarity) &&
  includesAny(asset.visualStyle, filters.visualStyle);

const queryBoost = (asset: Asset, query: string) => {
  const normalized = query.toLowerCase().trim();
  if (!normalized) return 0;

  return keywordRules.reduce((boost, rule) => {
    const hasKeyword = rule.keywords.some((keyword) => normalized.includes(keyword));
    if (!hasKeyword) return boost;
    const value = asset[rule.field];
    const matches = Array.isArray(value)
      ? rule.values.some((candidate) => value.includes(candidate))
      : rule.values.includes(value);
    return boost + (matches ? 8 : 0);
  }, asset.title.toLowerCase().includes(normalized) ? 12 : 0);
};

const calculateScore = (asset: Asset, request: SearchRequest) => {
  const { imageWeight, imageName, query } = request;
  const textWeight = 100 - imageWeight;
  const vectorBase = imageName ? asset.vectorSimilarity * (imageWeight / 100) : 0;
  const textBase = (asset.vectorSimilarity + queryBoost(asset, query)) * (textWeight / 100);
  const fallback = !imageName && !query ? asset.vectorSimilarity : 0;
  return vectorBase + textBase + asset.metadataMatch * 0.3 + fallback;
};

export async function searchAssets(request: SearchRequest): Promise<SearchResponse> {
  // Demo-only adapter: replace this body with a FastAPI request when the backend is ready.
  await new Promise((resolve) => setTimeout(resolve, 420));

  const scored = mockAssets
    .filter((asset) => matchesFilters(asset, request.filters))
    .map((asset) => ({ asset, score: calculateScore(asset, request) }))
    .sort((a, b) => {
      if (request.sort === "similarity") return b.asset.similarity - a.asset.similarity;
      if (request.sort === "match") return b.asset.metadataMatch - a.asset.metadataMatch;
      if (request.sort === "title") return a.asset.title.localeCompare(b.asset.title);
      return b.score - a.score;
    })
    .map(({ asset }) => asset);

  const totalCount = scored.length;
  const averageSimilarity = totalCount
    ? Math.round(scored.reduce((sum, asset) => sum + asset.similarity, 0) / totalCount)
    : 0;
  const conditionMatchRate = totalCount
    ? Math.round(scored.reduce((sum, asset) => sum + asset.metadataMatch, 0) / totalCount)
    : 0;

  return {
    results: scored,
    totalCount,
    averageSimilarity,
    conditionMatchRate,
    elapsedMs: 142
  };
}
