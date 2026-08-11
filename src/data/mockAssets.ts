import type { Asset } from "@/src/types/asset";

type Seed = Omit<Asset, "assetId" | "source" | "creator" | "sourceUrl" | "license" | "licenseCheckedAt"> &
  Partial<Pick<Asset, "source" | "creator" | "sourceUrl" | "license" | "licenseCheckedAt">>;

const source = {
  source: "OpenGameArt",
  creator: "arcane_studio",
  sourceUrl: "https://opengameart.org/",
  license: "CC0-1.0",
  licenseCheckedAt: "2026-07-20"
};

const seeds: Seed[] = [
  { title: "Azure Runeblade", descriptionKo: "푸른 룬 문양이 깃든 마법 양손검", weaponType: "검", colors: ["푸른색", "은색"], elements: ["얼음"], worldStyles: ["마법", "중세"], forms: ["양손", "장검"], rarity: "전설", visualStyle: "일러스트", similarity: 92, vectorSimilarity: 89, metadataMatch: 97, matchReasons: ["이미지 형태 96%", "푸른색 일치", "마법 속성 일치"], tone: "blue" },
  { title: "Flame Greatsword", descriptionKo: "붉은 불꽃 효과가 있는 판타지 양손검", weaponType: "검", colors: ["붉은색", "검은색"], elements: ["불"], worldStyles: ["마법", "고딕"], forms: ["양손", "장검"], rarity: "전설", visualStyle: "일러스트", similarity: 90, vectorSimilarity: 88, metadataMatch: 94, matchReasons: ["불 속성 일치", "양손 장검 형태", "고딕 스타일 일치"], tone: "red", creator: "example_creator" },
  { title: "Frostbite Spear", descriptionKo: "서리 결정이 맺힌 은빛 장창", weaponType: "창", colors: ["푸른색", "은색"], elements: ["얼음"], worldStyles: ["중세", "마법"], forms: ["양손", "대형"], rarity: "희귀", visualStyle: "아이콘", similarity: 87, vectorSimilarity: 88, metadataMatch: 85, matchReasons: ["얼음 속성 일치", "긴 실루엣 유사", "은색 재질 일치"], tone: "blue" },
  { title: "Stormcaller Staff", descriptionKo: "번개 수정이 박힌 마도사의 지팡이", weaponType: "지팡이", colors: ["보라색", "금색"], elements: ["번개"], worldStyles: ["마법", "엘프"], forms: ["대형", "곡선형"], rarity: "전설", visualStyle: "일러스트", similarity: 85, vectorSimilarity: 83, metadataMatch: 91, matchReasons: ["번개 속성 일치", "마법 스타일 일치", "보라색 광원"], tone: "violet" },
  { title: "Verdant Longbow", descriptionKo: "덩굴과 잎 장식이 있는 엘프 장궁", weaponType: "활", colors: ["녹색", "금색"], elements: ["독"], worldStyles: ["엘프", "중세"], forms: ["양손", "곡선형"], rarity: "희귀", visualStyle: "일러스트", similarity: 84, vectorSimilarity: 86, metadataMatch: 81, matchReasons: ["곡선형 실루엣", "엘프 스타일 일치", "녹색 장식"], tone: "green" },
  { title: "Obsidian Dagger", descriptionKo: "검은 화산 유리로 만든 은밀한 단검", weaponType: "검", colors: ["검은색", "보라색"], elements: ["암흑"], worldStyles: ["고딕", "오크"], forms: ["한손", "단검"], rarity: "희귀", visualStyle: "픽셀아트", similarity: 82, vectorSimilarity: 85, metadataMatch: 76, matchReasons: ["단검 형태 일치", "암흑 속성 일치", "검은색 재질"], tone: "slate" },
  { title: "Sunfire Axe", descriptionKo: "금빛 태양 문양과 불꽃 날을 지닌 전투 도끼", weaponType: "도끼", colors: ["금색", "붉은색"], elements: ["불"], worldStyles: ["중세", "신성"], forms: ["양손", "대형"], rarity: "전설", visualStyle: "아이콘", similarity: 81, vectorSimilarity: 78, metadataMatch: 89, matchReasons: ["불 속성 일치", "금색 장식 일치", "대형 도끼 형태"], tone: "orange" },
  { title: "Moonlit Buckler", descriptionKo: "달빛 문양이 새겨진 가벼운 원형 방패", weaponType: "방패", colors: ["은색", "푸른색"], elements: ["신성"], worldStyles: ["중세", "엘프"], forms: ["한손", "곡선형"], rarity: "일반", visualStyle: "아이콘", similarity: 79, vectorSimilarity: 80, metadataMatch: 77, matchReasons: ["은색 재질 일치", "방패 실루엣", "신성 태그 일치"], tone: "blue" },
  { title: "Venom Fang", descriptionKo: "독성 액체가 흐르는 오크 단검", weaponType: "검", colors: ["녹색", "검은색"], elements: ["독"], worldStyles: ["오크", "고딕"], forms: ["한손", "단검", "곡선형"], rarity: "희귀", visualStyle: "픽셀아트", similarity: 78, vectorSimilarity: 81, metadataMatch: 72, matchReasons: ["독 속성 일치", "곡선형 날", "픽셀아트 스타일"], tone: "green" },
  { title: "Silverguard Kite", descriptionKo: "기사단 문장이 있는 은빛 연 방패", weaponType: "방패", colors: ["은색", "푸른색"], elements: ["무속성"], worldStyles: ["중세"], forms: ["한손", "대형"], rarity: "일반", visualStyle: "일러스트", similarity: 76, vectorSimilarity: 77, metadataMatch: 74, matchReasons: ["중세 스타일", "은색 외형", "방패 형태"], tone: "slate" },
  { title: "Ember Pike", descriptionKo: "작은 불씨가 감도는 붉은 전투 창", weaponType: "창", colors: ["붉은색", "금색"], elements: ["불"], worldStyles: ["중세", "마법"], forms: ["양손", "대형"], rarity: "희귀", visualStyle: "픽셀아트", similarity: 75, vectorSimilarity: 79, metadataMatch: 67, matchReasons: ["불 속성 일치", "창 형태 일치", "붉은색 광원"], tone: "orange" },
  { title: "Celestial Scepter", descriptionKo: "별 조각을 담은 신성한 의식용 지팡이", weaponType: "지팡이", colors: ["금색", "은색"], elements: ["신성"], worldStyles: ["마법", "엘프"], forms: ["한손", "곡선형"], rarity: "전설", visualStyle: "아이콘", similarity: 74, vectorSimilarity: 72, metadataMatch: 79, matchReasons: ["신성 속성 일치", "금색 장식", "의식용 지팡이"], tone: "orange" },
  { title: "Glacier Halberd", descriptionKo: "빙하 조각처럼 날카로운 푸른 할버드", weaponType: "창", colors: ["푸른색", "은색"], elements: ["얼음"], worldStyles: ["중세"], forms: ["양손", "대형"], rarity: "전설", visualStyle: "일러스트", similarity: 73, vectorSimilarity: 76, metadataMatch: 66, matchReasons: ["얼음 속성 일치", "대형 무기 형태", "푸른색 일치"], tone: "blue" },
  { title: "Gilded Rapier", descriptionKo: "정교한 금 장식이 더해진 귀족의 세검", weaponType: "검", colors: ["금색", "은색"], elements: ["무속성"], worldStyles: ["중세", "고딕"], forms: ["한손", "장검"], rarity: "희귀", visualStyle: "일러스트", similarity: 72, vectorSimilarity: 75, metadataMatch: 64, matchReasons: ["금색 장식 일치", "한손 검 형태", "정교한 실루엣"], tone: "orange" },
  { title: "Nightwhisper Bow", descriptionKo: "암흑 안개로 감싼 검은 사냥 활", weaponType: "활", colors: ["검은색", "보라색"], elements: ["암흑"], worldStyles: ["고딕", "엘프"], forms: ["양손", "곡선형"], rarity: "희귀", visualStyle: "픽셀아트", similarity: 71, vectorSimilarity: 74, metadataMatch: 62, matchReasons: ["암흑 속성 일치", "활 실루엣", "고딕 분위기"], tone: "violet" },
  { title: "Ironroot Cleaver", descriptionKo: "거친 철과 뿌리 장식으로 만든 오크 도끼", weaponType: "도끼", colors: ["녹색", "검은색"], elements: ["무속성"], worldStyles: ["오크"], forms: ["한손", "대형"], rarity: "일반", visualStyle: "아이콘", similarity: 69, vectorSimilarity: 71, metadataMatch: 63, matchReasons: ["오크 스타일", "도끼 형태", "거친 재질"], tone: "green" },
  { title: "Radiant Saber", descriptionKo: "백색 빛을 두른 성기사의 곡선 검", weaponType: "검", colors: ["금색", "은색"], elements: ["신성"], worldStyles: ["중세", "마법"], forms: ["한손", "곡선형"], rarity: "전설", visualStyle: "일러스트", similarity: 68, vectorSimilarity: 69, metadataMatch: 65, matchReasons: ["신성 속성 일치", "곡선형 검", "금색 일치"], tone: "orange" },
  { title: "Cinder Ward", descriptionKo: "그을린 철판에 불꽃 문양을 새긴 방패", weaponType: "방패", colors: ["붉은색", "검은색"], elements: ["불"], worldStyles: ["고딕", "중세"], forms: ["한손", "대형"], rarity: "일반", visualStyle: "픽셀아트", similarity: 66, vectorSimilarity: 68, metadataMatch: 61, matchReasons: ["불 속성 일치", "검은색 외형", "방패 형태"], tone: "red" }
];

export const mockAssets: Asset[] = seeds.map((asset, index) => ({
  ...source,
  ...asset,
  assetId: `ARC-${String(index + 1).padStart(4, "0")}`
}));
