# 데이터 분리 안내

검수 완료된 총 1,113개 에셋을 유사 이미지 그룹 단위로 분리했습니다.

- train: 886개
- validation: 115개
- test: 112개
- 분할 비율 목표: 80% / 10% / 10%
- 고정 시드: 20260807
- 유사 이미지 기준: 같은 카테고리에서 perceptual hash 해밍 거리 2 이하

`train.jsonl`, `validation.jsonl`, `test.jsonl`은 학습·검증·최종 평가에 각각 사용합니다.
`split_manifest.jsonl`은 각 에셋의 소속과 유사 이미지 그룹을 확인하는 표입니다.
`split_summary.json`은 분할 수와 카테고리 분포를 담고 있습니다.
