import { WeaponVisual } from "@/src/components/WeaponVisual";
import { displayValue, type Locale } from "@/src/lib/labels";
import type { Asset } from "@/src/types/asset";

const rarityClass: Record<string, string> = { common: "rarity-common", legendary: "rarity-legendary" };

export function ResultCard({ asset, locale, onDetails, onSimilar }: { asset: Asset; locale: Locale; onDetails: (asset: Asset) => void; onSimilar: (asset: Asset) => Promise<void> | void }) {
  const tags = [asset.category, asset.colors[0], asset.elements[0], asset.visualStyle].filter((value): value is string => Boolean(value));
  const description = locale === "ko" ? asset.descriptionKo : asset.descriptionEn;
  const reasons = locale === "ko" ? asset.matchReasons : [asset.imageSimilarity === null ? null : `Image similarity ${asset.imageSimilarity}%`, asset.textSimilarity === null ? null : `Text similarity ${asset.textSimilarity}%`, asset.colors.length ? `Colors: ${asset.colors.slice(0, 2).map((color) => displayValue(color, locale)).join(", ")}` : null, asset.elements.length ? `Elements: ${asset.elements.map((element) => displayValue(element, locale)).join(", ")}` : null].filter((reason): reason is string => Boolean(reason));
  return (
    <article className="result-card">
      <div className="result-image-wrap">
        <WeaponVisual asset={asset} alt={description} />
        {asset.grade && <span className={`rarity-badge ${rarityClass[asset.grade] ?? "rarity-common"}`}>{displayValue(asset.grade, locale)}</span>}
      </div>
      <div className="result-body">
        <div className="result-heading">
          <div><h3>{displayValue(asset.title, locale)}</h3><p>{description}</p></div>
          <strong>{asset.similarity}%</strong>
        </div>
        <div className="similarity-track" role="progressbar" aria-label={`종합 유사도 ${asset.similarity}%`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={asset.similarity}><span style={{ width: `${asset.similarity}%` }} /></div>
        <div className="tag-list">
          {tags.map((tag) => <span key={tag}>{displayValue(tag, locale)}</span>)}
        </div>
        {reasons.length > 0 && <ul className="reason-list">
          {reasons.slice(0, 3).map((reason) => <li key={reason}>✓ {reason}</li>)}
        </ul>}
        <div className="card-actions">
          <button className="text-button" onClick={() => onDetails(asset)}>{locale === "ko" ? "자세히 보기" : "View details"}</button>
          <button className="text-button" onClick={() => void onSimilar(asset)}>{locale === "ko" ? "유사 에셋 검색" : "Find similar"}</button>
        </div>
      </div>
    </article>
  );
}
