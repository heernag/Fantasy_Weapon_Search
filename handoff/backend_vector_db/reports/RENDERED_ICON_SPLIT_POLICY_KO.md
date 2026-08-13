# 렌더 아이콘 데이터셋 split 정책

렌더 아이콘은 픽셀아트와 일러스트와 시각적 특성이 달라, 독립된 `rendered_icon` split으로 관리합니다.

- 대상 수: 150개
- 분할: train 121개, validation 15개, test 14개
- 고정 시드: `20260812`
- 분할 단위: 동일 perceptual hash 변형 그룹
- 검증: split 간 ID 중복 0건, 변형 그룹 누수 0건

검색·평가 시에는 `data/splits/rendered_icon/`의 후보만 사용하며, 픽셀아트·일러스트 후보와 섞지 않습니다.
