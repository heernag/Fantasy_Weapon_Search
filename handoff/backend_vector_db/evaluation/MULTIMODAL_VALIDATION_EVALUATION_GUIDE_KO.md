# 이미지·문장 결합검색 validation 평가 안내

이미지 임베딩과 문장 임베딩의 결합 가중치를 선택하기 위한 validation 전용 평가 세트입니다.

## 범위

- 후보 이미지: `data/splits/validation.jsonl`의 픽셀아트 94개
- 질의: 한글 40개, 영어 40개, 총 80개
- 정답: `multimodal_validation_ground_truth.jsonl`에 있는 validation 에셋 ID만 사용
- 변경 유형: `color_change`, `element_change`, `material_change`, `style_change`
- 유지 조건: 모든 질의는 원본과 동일한 `category`, `subcategory`를 유지
- 스타일 변경: 전체 `visual_style`이 아닌 `style_variant`를 기준으로 평가

## 사용 방법

1. 기준 이미지의 임베딩과 수정 문장의 임베딩을 여러 가중치로 결합합니다.
2. validation 후보 94개 안에서만 검색합니다.
3. 각 가중치별 Recall@K, MRR, mAP를 계산합니다.
4. 가장 좋은 결과를 낸 가중치를 고정한 뒤, test 평가 세트에는 한 번만 적용합니다.

`test` 결과를 보고 가중치를 다시 바꾸면 평가 점수가 과대평가될 수 있으므로, 가중치 선택에는 이 validation 세트만 사용합니다.
