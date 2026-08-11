import { WeaponVisual } from "@/src/components/WeaponVisual";
import type { Asset } from "@/src/types/asset";

export function AssetDetail({ asset, onClose, onSimilar }: { asset: Asset | null; onClose: () => void; onSimilar: (asset: Asset) => void }) {
  if (!asset) return null;
  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="detail-sheet" role="dialog" aria-modal="true" aria-labelledby="asset-detail-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="sheet-top"><div><span className="section-label">에셋 상세</span><h2 id="asset-detail-title">{asset.title}</h2></div><button className="icon-button" aria-label="상세 보기 닫기" onClick={onClose}>×</button></div>
        <WeaponVisual asset={asset} large />
        <p className="detail-description">{asset.descriptionKo}</p>
        <section className="score-breakdown"><h3>점수 분해</h3><div><span>벡터 유사도</span><strong>{asset.vectorSimilarity}%</strong></div><div><span>메타데이터 일치</span><strong>{asset.metadataMatch}%</strong></div><div><span>최종 유사도</span><strong>{asset.similarity}%</strong></div></section>
        <section className="detail-section"><h3>메타데이터</h3><dl className="metadata-list"><div><dt>무기 종류</dt><dd>{asset.weaponType}</dd></div><div><dt>색상</dt><dd>{asset.colors.join(" · ")}</dd></div><div><dt>속성</dt><dd>{asset.elements.join(" · ")}</dd></div><div><dt>스타일</dt><dd>{asset.worldStyles.join(" · ")} / {asset.visualStyle}</dd></div><div><dt>형태</dt><dd>{asset.forms.join(" · ")}</dd></div><div><dt>희귀도</dt><dd>{asset.rarity}</dd></div></dl></section>
        <section className="detail-section"><h3>출처 및 라이선스</h3><dl className="metadata-list"><div><dt>출처</dt><dd>{asset.source}</dd></div><div><dt>제작자</dt><dd>{asset.creator}</dd></div><div><dt>라이선스</dt><dd>{asset.license}</dd></div><div><dt>확인일</dt><dd>{asset.licenseCheckedAt}</dd></div></dl></section>
        <div className="sheet-actions"><button className="secondary-button" onClick={() => onSimilar(asset)}>유사 에셋 검색</button><a className="primary-button" href={asset.sourceUrl} target="_blank" rel="noreferrer">원본 페이지 열기 ↗</a></div>
      </aside>
    </div>
  );
}
