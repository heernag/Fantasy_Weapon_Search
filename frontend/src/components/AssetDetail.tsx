import { WeaponVisual } from "@/src/components/WeaponVisual";
import { displayValue, type Locale } from "@/src/lib/labels";
import type { Asset } from "@/src/types/asset";

function valueOrFallback(values: string[], locale: Locale, empty = locale === "ko" ? "정보 없음" : "Not available") {
  return values.length ? values.map((value) => displayValue(value, locale)).join(" · ") : empty;
}

export function AssetDetail({ asset, locale, onClose, onSimilar }: { asset: Asset | null; locale: Locale; onClose: () => void; onSimilar: (asset: Asset) => Promise<void> | void }) {
  if (!asset) return null;
  const description = locale === "ko" ? asset.descriptionKo : asset.descriptionEn;
  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="detail-sheet" role="dialog" aria-modal="true" aria-labelledby="asset-detail-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="sheet-top"><div><span className="section-label">{locale === "ko" ? "에셋 상세" : "Asset details"}</span><h2 id="asset-detail-title">{displayValue(asset.title, locale)}</h2></div><button className="icon-button" aria-label={locale === "ko" ? "상세 보기 닫기" : "Close details"} onClick={onClose}>×</button></div>
        <WeaponVisual asset={asset} alt={description} large />
        <p className="detail-description">{description}</p>
        <section className="score-breakdown"><h3>{locale === "ko" ? "검색 점수" : "Search score"}</h3><div><span>{locale === "ko" ? "최종 유사도" : "Final similarity"}</span><strong>{asset.similarity}%</strong></div>{asset.imageSimilarity !== null && <div><span>{locale === "ko" ? "이미지 유사도" : "Image similarity"}</span><strong>{asset.imageSimilarity}%</strong></div>}{asset.textSimilarity !== null && <div><span>{locale === "ko" ? "텍스트 유사도" : "Text similarity"}</span><strong>{asset.textSimilarity}%</strong></div>}</section>
        <section className="detail-section"><h3>{locale === "ko" ? "메타데이터" : "Metadata"}</h3><dl className="metadata-list"><div><dt>{locale === "ko" ? "무기 종류" : "Weapon type"}</dt><dd>{displayValue(asset.category, locale)}</dd></div><div><dt>{locale === "ko" ? "세부 종류" : "Subtype"}</dt><dd>{displayValue(asset.subcategory, locale)}</dd></div><div><dt>{locale === "ko" ? "색상" : "Colors"}</dt><dd>{valueOrFallback(asset.colors, locale)}</dd></div><div><dt>{locale === "ko" ? "속성" : "Elements"}</dt><dd>{valueOrFallback(asset.elements, locale, locale === "ko" ? "무속성" : "Non-elemental")}</dd></div><div><dt>{locale === "ko" ? "재질" : "Materials"}</dt><dd>{valueOrFallback(asset.materials, locale)}</dd></div><div><dt>{locale === "ko" ? "스타일" : "Style"}</dt><dd>{displayValue(asset.style, locale)} / {displayValue(asset.visualStyle, locale)}</dd></div><div><dt>{locale === "ko" ? "등급" : "Rarity"}</dt><dd>{displayValue(asset.grade, locale)}</dd></div></dl></section>
        <section className="detail-section"><h3>{locale === "ko" ? "출처 및 라이선스" : "Source & license"}</h3><dl className="metadata-list"><div><dt>{locale === "ko" ? "출처" : "Source"}</dt><dd>{asset.source ?? displayValue(null, locale)}</dd></div><div><dt>{locale === "ko" ? "제작자" : "Creator"}</dt><dd>{asset.creator ?? displayValue(null, locale)}</dd></div><div><dt>{locale === "ko" ? "라이선스" : "License"}</dt><dd>{asset.license ?? displayValue(null, locale)}</dd></div><div><dt>{locale === "ko" ? "검증 상태" : "Verification"}</dt><dd>{asset.licenseStatus ?? displayValue(null, locale)}</dd></div></dl></section>
        <div className="sheet-actions"><button className="secondary-button" onClick={() => void onSimilar(asset)}>{locale === "ko" ? "유사 에셋 검색" : "Find similar"}</button>{asset.sourceUrl && <a className="primary-button" href={asset.sourceUrl} target="_blank" rel="noreferrer">{locale === "ko" ? "원본 페이지 열기 ↗" : "Open source page ↗"}</a>}</div>
      </aside>
    </div>
  );
}
