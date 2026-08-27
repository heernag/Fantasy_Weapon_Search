import Image from "next/image";
import type { Asset } from "@/src/types/asset";

export function WeaponVisual({ asset, alt, large = false }: { asset: Asset; alt: string; large?: boolean }) {
  return (
    <div className={large ? "weapon-visual weapon-large" : "weapon-visual"}>
      <Image
        src={asset.imageUrl}
        alt={alt}
        width={asset.imageWidth}
        height={asset.imageHeight}
        loading={large ? "eager" : "lazy"}
        preload={large}
        sizes={large ? "(max-width: 488px) 100vw, 488px" : "(max-width: 620px) 100vw, (max-width: 900px) 50vw, 300px"}
      />
    </div>
  );
}
