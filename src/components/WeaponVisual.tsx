import type { Asset } from "@/src/types/asset";

const palettes = {
  violet: { core: "oklch(0.5 0.16 290)", glow: "oklch(0.92 0.045 290)", dark: "oklch(0.28 0.07 290)" },
  blue: { core: "oklch(0.52 0.13 246)", glow: "oklch(0.93 0.03 246)", dark: "oklch(0.28 0.06 246)" },
  orange: { core: "oklch(0.58 0.13 58)", glow: "oklch(0.94 0.04 58)", dark: "oklch(0.3 0.07 58)" },
  green: { core: "oklch(0.53 0.11 157)", glow: "oklch(0.93 0.03 157)", dark: "oklch(0.27 0.06 157)" },
  slate: { core: "oklch(0.47 0.025 260)", glow: "oklch(0.92 0.01 260)", dark: "oklch(0.25 0.02 260)" },
  red: { core: "oklch(0.53 0.15 22)", glow: "oklch(0.94 0.035 22)", dark: "oklch(0.3 0.06 22)" }
};

export function WeaponVisual({ asset, large = false }: { asset: Asset; large?: boolean }) {
  const color = palettes[asset.tone];
  const size = large ? 280 : 152;

  return (
    <div className={`weapon-visual weapon-${asset.tone} ${large ? "weapon-large" : ""}`} aria-label={`${asset.title} 목업 이미지`}>
      <svg width={size} height={large ? 230 : 128} viewBox="0 0 160 128" role="img" aria-hidden="true">
        <defs>
          <linearGradient id={`core-${asset.assetId}`} x1="0" x2="1" y1="0" y2="1">
            <stop stopColor={color.glow} />
            <stop offset="1" stopColor={color.core} />
          </linearGradient>
        </defs>
        <circle cx="80" cy="64" r="48" fill={color.glow} opacity=".55" />
        {asset.weaponType === "검" && <><path d="M84 16 101 72 89 92 75 70Z" fill={`url(#core-${asset.assetId})`} stroke={color.dark} strokeWidth="3"/><path d="m58 88 49-13 3 10-49 14Z" fill={color.dark}/><path d="m78 90 11-3 10 25-16 4Z" fill={color.core}/></>}
        {asset.weaponType === "도끼" && <><path d="m85 17 9 87-13 2-9-87Z" fill={color.dark}/><path d="M54 34c29-22 54-5 51 25-5 15-20 24-39 23l-11-11c13-3 19-14 18-25-1-6-7-10-19-7Z" fill={`url(#core-${asset.assetId})`} stroke={color.dark} strokeWidth="3"/></>}
        {asset.weaponType === "창" && <><path d="m76 17 10 95-10 2-10-95Z" fill={color.dark}/><path d="m81 13 18 31-18 11-18-11Z" fill={`url(#core-${asset.assetId})`} stroke={color.dark} strokeWidth="3"/></>}
        {asset.weaponType === "활" && <><path d="M58 18c50 12 50 80 0 92" fill="none" stroke={color.core} strokeWidth="10" strokeLinecap="round"/><path d="M61 20 102 110" stroke={color.dark} strokeWidth="2"/><path d="m55 66 50 0" stroke={color.dark} strokeWidth="4"/><path d="m101 60 14 6-14 6" fill={color.dark}/></>}
        {asset.weaponType === "지팡이" && <><path d="m78 28 10 86-13 1-9-86Z" fill={color.dark}/><circle cx="80" cy="22" r="16" fill={`url(#core-${asset.assetId})`} stroke={color.dark} strokeWidth="3"/><path d="m80 10 4 9 10 3-10 4-4 10-4-10-10-4 10-3Z" fill="oklch(1 0 0)" opacity=".85"/></>}
        {asset.weaponType === "방패" && <><path d="M80 14c22 10 34 12 34 12v41c0 24-19 39-34 47-15-8-34-23-34-47V26s12-2 34-12Z" fill={`url(#core-${asset.assetId})`} stroke={color.dark} strokeWidth="3"/><path d="m80 30 7 22 20 0-16 13 6 22-17-13-17 13 6-22-16-13h20Z" fill={color.glow} opacity=".9"/></>}
      </svg>
    </div>
  );
}
