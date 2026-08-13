# 이미지＋문장 결합검색 평가 세트 제작·사용 안내서

## 1. 무엇을 평가하나요?

일반 텍스트 검색은 “파란색 장검”처럼 문장만 입력합니다. 이미지＋문장 결합검색은 다음 두 가지를 함께 입력합니다.

1. 기준이 되는 무기 이미지
2. 기준 이미지에서 바꾸고 싶은 내용을 적은 문장

예를 들어 파란 장검 이미지를 보여주면서 “붉은색 계열로 바꿔줘”라고 입력하면, 검색 시스템은 모양과 무기 종류는 비슷하지만 붉은색인 장검을 찾아야 합니다.

## 2. 현재 평가 세트 구성

- 검색 후보: `data/splits/test.jsonl`의 픽셀아트 92개
- 변환 개념: 40개
- 한국어 질의: 40개
- 영어 질의: 40개
- 전체 질의: 80개

| 변환 유형 | 개념 수 | 의미 |
|---|---:|---|
| `color_change` | 16 | 기준 이미지의 주 색상을 변경 |
| `element_change` | 10 | 불·얼음·어둠 등의 속성을 변경 |
| `material_change` | 10 | 강철·나무·수정 등의 재질을 변경 |
| `style_change` | 4 | 중세·판타지·다크 판타지 등의 양식을 변경 |

## 3. 파일 설명

### `multimodal_queries.jsonl`

검색 시스템에 전달할 기준 이미지와 수정 문장이 들어 있습니다.

```json
{
  "query_id": "mm_ko_001",
  "concept_id": "mm_concept_001",
  "language": "ko",
  "query_type": "color_change",
  "query_image_id": "asset_000339",
  "query_image": "data/processed/pixel_art/asset_000339.png",
  "modification_text": "회색 계열로 바꿔줘",
  "preserve_filters": {
    "category": "axe",
    "subcategory": "broad_axe"
  },
  "target_filters": {
    "primary_color": "gray"
  },
  "excluded_asset_ids": [
    "asset_000339"
  ],
  "candidate_split": "test"
}
```

- `query_image`: 모델에 입력할 기준 이미지 경로
- `modification_text`: 이미지에서 바꾸고 싶은 내용
- `preserve_filters`: 그대로 유지해야 하는 무기 종류
- `target_filters`: 문장이 요구하는 목표 속성
- `excluded_asset_ids`: 검색 결과에서 제외할 기준 이미지

### `multimodal_ground_truth.jsonl`

각 질의에 대한 정답 이미지 ID가 들어 있습니다.

```json
{
  "query_id": "mm_ko_001",
  "concept_id": "mm_concept_001",
  "query_image_id": "asset_000339",
  "relevant_asset_ids": [
    "asset_000338"
  ],
  "relevance": "binary",
  "candidate_split": "test"
}
```

### `multimodal_evaluation_summary.json`

질의 개수, 유형별 개수, 사용된 무기 종류와 정답 개수 범위를 요약합니다.

## 4. 평가 데이터를 만든 방법

### 1단계: 같은 무기끼리 묶기

test 이미지 92개를 `category + subcategory` 기준으로 묶었습니다. 장검은 장검끼리, 손도끼는 손도끼끼리 비교합니다.

### 2단계: 기준 이미지와 목표값 선택

같은 그룹 안에서 다음 값이 다른 이미지 짝을 찾았습니다.

- 색상: `primary_color`
- 속성: `elements`
- 재질: `materials`
- 양식: `style`

기준 이미지가 이미 목표값을 가지고 있으면 해당 조합은 사용하지 않았습니다.

### 3단계: 정답 계산

정답은 다음 조건을 모두 만족해야 합니다.

1. 현재 test split에 포함되어 있음
2. 기준 이미지와 다른 에셋임
3. 기준 이미지와 `category`, `subcategory`가 같음
4. 수정 문장이 요구한 목표 필터를 만족함

조건을 만족하는 이미지가 여러 개면 모두 정답으로 기록합니다.

### 4단계: 한글·영문 쌍 만들기

같은 개념을 한국어와 영어로 각각 만들었습니다. 두 질의는 기준 이미지, 필터, 정답을 공유합니다.

예시:

- 한국어: `어둠 속성이 있는 것으로 바꿔줘`
- 영어: `change it to one with dark elemental traits`

### 5단계: 자동 검증

다음 오류가 없는지 검사했습니다.

- 기준 이미지나 정답이 test 밖에 있는 경우
- 기준 이미지가 자신의 정답으로 들어간 경우
- 정답이 하나도 없는 경우
- 한글과 영어의 조건 또는 정답이 다른 경우
- 실제 메타데이터와 목표 필터가 다른 경우
- 분리된 렌더 아이콘이나 일러스트가 섞인 경우

## 5. 파일을 다시 만드는 방법

test split이나 메타데이터가 변경되면 프로젝트 폴더에서 다음 생성기를 실행합니다.

```powershell
python scripts\generate_multimodal_evaluation.py
```

생성 후 반드시 검증기를 실행합니다.

```powershell
python scripts\validate_multimodal_evaluation.py
```

검증 결과에 `결합검색 평가 세트 검증 통과`가 표시되어야 합니다.

## 6. 검색 모델 담당자가 사용하는 방법

1. `query_image`의 이미지를 이미지 인코더에 넣어 이미지 임베딩을 만듭니다.
2. `modification_text`를 텍스트 인코더에 넣어 텍스트 임베딩을 만듭니다.
3. 이미지 임베딩과 텍스트 임베딩을 결합합니다.
4. test 92개의 이미지 임베딩과 유사도를 계산합니다.
5. `excluded_asset_ids`에 있는 기준 이미지를 결과에서 제거합니다.
6. 상위 검색 결과를 `relevant_asset_ids`와 비교합니다.

간단한 결합 방식은 다음과 같습니다.

```text
결합 임베딩 = 이미지 임베딩 × 이미지 가중치 + 텍스트 임베딩 × 텍스트 가중치
```

초기 실험에서는 이미지 0.6, 텍스트 0.4로 시작할 수 있습니다. 이후 validation 실험으로 가중치를 조정해야 하며, test 결과를 보고 가중치를 바꾸면 안 됩니다.

## 7. 권장 평가 지표

- `Recall@1`, `Recall@5`, `Recall@10`: 정답을 상위 K개 안에서 찾았는지 평가
- `MRR`: 첫 번째 정답이 얼마나 빨리 나오는지 평가
- `mAP`: 정답이 여러 개인 질의의 전체 검색 순위를 평가
- 유형별 Recall: 색상·속성·재질·스타일 변경 성능을 따로 비교
- 언어별 Recall: 같은 개념의 한국어와 영어 성능을 비교

## 8. 주의사항

- 이 평가 파일은 모델 학습에 사용하면 안 됩니다.
- test split이 변경되면 평가 파일도 반드시 다시 생성해야 합니다.
- 기준 이미지를 검색 정답으로 인정하면 결합검색 능력이 과대평가되므로 반드시 제외해야 합니다.
- 현재 평가는 픽셀아트 전용입니다. 렌더 아이콘과 일러스트에는 별도 평가 세트가 필요합니다.
- 자동 생성 정답은 메타데이터 기반 이진 정답입니다. 최종 발표 전에는 사람이 결과 이미지가 실제로 자연스러운 정답인지 표본 검수하는 것이 좋습니다.
