# REDTEAM 데이터 점검 보고서

- 갱신일: 2026-08-13
- 기준: 최종 메타데이터 및 split/evaluation JSONL

## 통과

- 1,391개 에셋의 메타데이터·이미지 연결, 출처·라이선스, 한글/영문 캡션, 태그 스키마를 확인했습니다.
- 세 스타일의 split 합계가 메타데이터 수와 일치합니다.
- train/validation/test 간 에셋 ID 중복은 없습니다.
- perceptual hash 기반 변형 그룹을 split 안에 묶어 일러스트·렌더 아이콘 교차 split 누수는 0그룹입니다.
- 평가 질의와 ground truth의 행 수가 일치합니다: 텍스트 160, 이미지+문장 80, 일러스트 100.
- manifest SHA-256은 pretty JSON을 해시 대상으로 사용하며, JSONL과의 직렬화 차이는 불일치가 아닙니다.

## 남은 운영 단계

- 실제 CLIP 임베딩 생성과 검색 지표(Recall@K, MRR, mAP) 측정은 백엔드·모델 환경에서 수행합니다.
- 새 에셋을 추가하거나 태그를 수정할 때는 `scripts/rebuild_ground_truth_and_manifest.py`를 실행해 split 요약, 평가 통계, manifest, handoff를 함께 재생성해야 합니다.
