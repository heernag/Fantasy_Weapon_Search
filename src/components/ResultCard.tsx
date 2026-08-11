import { WeaponVisual } from "@/src/components/WeaponVisual";
import type { Asset } from "@/src/types/asset";

const rarityClass = { 일반: "rarity-common", 희귀: "rarity-rare", 전설: "rarity-legendary" };

export function ResultCard({ asset, onDetails, onSimilar }: { asset: Asset; onDetails: (asset: Asset) => void; onSimilar: (asset: Asset) => void }) {
  return (
    <article className="result-card">
      <div className="result-image-wrap">
        <WeaponVisual asset={asset} />
        <span className={`rarity-badge ${rarityClass[asset.rarity]}`}>{asset.rarity}</span>
      </div>
      <div className="result-body">
        <div className="result-heading">
          <div><h3>{asset.title}</h3><p>{asset.descriptionKo}</p></div>
          <strong>{asset.similarity}%</strong>
        </div>
        <div className="similarity-track" aria-label={`종합 유사도 ${asset.similarity}%`}><span style={{ width: `${asset.similarity}%` }} /></div>
        <div className="tag-list">
          <span>{asset.weaponType}</span><span>{asset.colors[0]}</span><span>{asset.elements[0]}</span><span>{asset.visualStyle}</span>
        </div>
        <ul className="reason-list">
          {asset.matchReasons.slice(0, 3).map((reason) => <li key={reason}>✓ {reason}</li>)}
        </ul>
        <div className="card-actions">
          <button className="text-button" onClick={() => onDetails(asset)}>자세히 보기</button>
          <button className="text-button" onClick={() => onSimilar(asset)}>유사 에셋 검색</button>
        </div>
      </div>
    </article>
  );
}
