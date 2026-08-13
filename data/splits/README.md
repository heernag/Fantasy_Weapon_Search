# 데이터 분리 안내

최종 메타데이터 1,391개를 데이터셋별 유사 이미지 그룹 단위로 분리했습니다.

- 픽셀아트: train 772개 / validation 94개 / test 91개
- 일러스트: train 230개 / validation 27개 / test 27개
- 렌더 아이콘: train 120개 / validation 15개 / test 15개
- 분할 비율 목표: 80% / 10% / 10%
- 고정 시드: 20260807
- 유사 이미지 기준: 같은 카테고리에서 perceptual hash 해밍 거리 2 이하

루트의 `train.jsonl`, `validation.jsonl`, `test.jsonl`은 픽셀아트 split이며, `illustration/`과 `rendered_icon/` 하위에도 동일한 구조를 제공합니다.
`split_manifest.jsonl`은 각 에셋의 소속과 유사 이미지 그룹을 확인하는 표입니다.
`split_summary.json`은 분할 수와 카테고리 분포를 담고 있습니다.
