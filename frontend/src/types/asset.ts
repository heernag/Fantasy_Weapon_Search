export const scalarFilterKeys = [
  "visual_style",
  "category",
  "subcategory",
  "primary_color",
  "grade",
  "style",
  "handedness"
] as const;

export const listFilterKeys = ["colors", "elements", "materials", "shape_tags"] as const;

export type ScalarFilterKey = (typeof scalarFilterKeys)[number];
export type ListFilterKey = (typeof listFilterKeys)[number];
export type FilterKey = ScalarFilterKey | ListFilterKey;

export type SearchFilters = Record<ScalarFilterKey, string | null> & Record<ListFilterKey, string[]>;

export type FilterOption = { value: string; count: number };
export type FilterCatalog = Partial<Record<FilterKey, FilterOption[]>>;

export type ApiAssetMetadata = {
  processed_width?: number;
  processed_height?: number;
  author?: string;
  source_name?: string;
  source?: string;
  source_url?: string;
  license?: string;
  license_status?: string;
};

export type ApiSearchHit = {
  asset_id: string;
  score: number;
  image_url: string;
  image_path: string;
  result_text: string;
  metadata: ApiAssetMetadata & Record<string, unknown>;
  combined_score?: number;
  image_score?: number;
  text_score?: number;
  visual_style?: string;
  category?: string;
  subcategory?: string;
  primary_color?: string;
  colors?: string[];
  materials?: string[];
  elements?: string[];
  shape_tags?: string[];
  grade?: string;
  handedness?: string;
  style?: string;
  caption_en?: string;
  caption_ko?: string;
  source?: string;
  source_url?: string;
  license?: string;
};

export type ApiSearchResponse = {
  search_type: string;
  query_type: string;
  query_text?: string | null;
  translated_text?: string | null;
  image_weight?: number | null;
  text_weight?: number | null;
  top_k: number;
  offset: number;
  candidate_count: number;
  retrievable_count: number;
  elapsed_ms: number;
  search_elapsed_ms: number;
  results: ApiSearchHit[];
};

export type Asset = {
  assetId: string;
  title: string;
  descriptionKo: string;
  descriptionEn: string;
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  category: string;
  subcategory: string | null;
  colors: string[];
  elements: string[];
  materials: string[];
  shapeTags: string[];
  grade: string | null;
  visualStyle: string | null;
  style: string | null;
  handedness: string | null;
  similarity: number;
  imageSimilarity: number | null;
  textSimilarity: number | null;
  source: string | null;
  creator: string | null;
  sourceUrl: string | null;
  license: string | null;
  licenseStatus: string | null;
  matchReasons: string[];
};

export type SearchRequest = {
  query: string;
  image?: File;
  imageWeight: number;
  filters: SearchFilters;
  topK: number;
  offset: number;
};

export type SearchResponse = {
  results: Asset[];
  totalCount: number;
  retrievableCount: number;
  elapsedMs: number;
  searchElapsedMs: number;
  searchType: string;
  queryType: string;
  topK: number;
  offset: number;
};

export const emptyFilters: SearchFilters = {
  visual_style: null,
  category: null,
  subcategory: null,
  primary_color: null,
  grade: null,
  style: null,
  handedness: null,
  colors: [],
  elements: [],
  materials: [],
  shape_tags: []
};
