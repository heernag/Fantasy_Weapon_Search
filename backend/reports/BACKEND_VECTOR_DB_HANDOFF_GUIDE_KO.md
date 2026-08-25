# 백엔드·Vector DB 작업 전달 보고서

## 1. 기준 데이터

백엔드는 아래 최종 manifest를 기준으로 작업한다.

- 기준 manifest: `data/metadata/final_manifest.json`
- 최종 메타데이터: `data/metadata/final_search_assets_pretty.json`
- 총 에셋: 1,391개
- 픽셀아트: 957개
- 일러스트: 284개
- 렌더 아이콘: 150개

manifest의 `status`가 `final`인지 확인하고, 메타데이터 SHA-256이 일치할 때만 임베딩을 생성한다.

## 2. 임베딩 대상과 split

스타일별 split은 서로 독립적이다.

| 스타일 | train | validation | test |
|---|---:|---:|---:|
| pixel_art | 772 | 94 | 91 |
| illustration | 229 | 18 | 37 |
| rendered_icon | 121 | 15 | 14 |

- 픽셀아트: `data/splits/train.jsonl`, `validation.jsonl`, `test.jsonl`
- 일러스트: `data/splits/illustration/`
- 렌더 아이콘: `data/splits/rendered_icon/`

각 JSONL의 `asset_id`를 기준으로 이미지와 메타데이터를 연결한다. 파일 경로는 행의 `processed_file`을 사용한다.

## 3. CLIP 임베딩 생성

1. 백엔드 환경에 PyTorch와 OpenCLIP 또는 호환 CLIP 라이브러리를 설치한다.
2. 고정된 모델명·가중치·전처리·정규화 방식을 기록한다.
3. 이미지 임베딩과 텍스트 임베딩을 각각 생성한다.
4. 임베딩 행마다 `asset_id`, 모델 버전, 생성일, 차원, 정규화 여부를 기록한다.
5. 이미지·텍스트 임베딩의 행 순서가 split JSONL의 `asset_id` 순서와 일치하는지 확인한다.
6. 임베딩 파일에는 최종 메타데이터 전체를 복사하지 말고 `asset_id`와 필요한 검색 필드만 저장한다.

권장 저장 구조:

```text
embeddings/
  model_info.json
  pixel_art/image_embeddings.*
  pixel_art/text_embeddings.*
  illustration/image_embeddings.*
  illustration/text_embeddings.*
  rendered_icon/image_embeddings.*
  rendered_icon/text_embeddings.*
```

## 4. Vector DB 적재

필수 payload 필드:

- `asset_id`
- `visual_style`
- `category`
- `subcategory`
- `primary_color`
- `colors`
- `elements`
- `materials`
- `handedness`
- `grade`
- `caption_ko`, `caption_en`
- `source`, `source_url`, `license`
- `processed_file`

검색 시 `visual_style`, category, 색상, 속성, 재질, 등급 필터를 적용할 수 있어야 한다. `elements`가 빈 배열이면 무속성(common), 값이 있으면 전설 등급(legendary)이라는 현재 데이터 규칙도 유지한다.

## 5. 출처 필드 매핑

현재 1,391개 모두 `source_url`을 사용한다. API가 `source`만 반환하거나 읽는 경우 다음 규칙을 적용한다.

```text
API source = metadata.source_url
원본 출처가 필요한 경우 metadata.source_file/source_url을 별도 보존
```

`source`와 `source_url`을 임의로 삭제하거나 서로 다른 값으로 덮어쓰지 않는다.

## 6. 평가 실행

평가 파일:

- 텍스트 검색: `data/evaluation/evaluation_queries.jsonl`, `ground_truth.jsonl`
- 이미지+문장 검색: `multimodal_queries.jsonl`, `multimodal_ground_truth.jsonl`
- 일러스트 검색: `illustration_evaluation_queries.jsonl`, `illustration_ground_truth.jsonl`

정답 ID는 질의 파일이 아니라 ground-truth 파일에서 읽는다. 현재 행 수는 각각 텍스트 160개, 멀티모달 80개, 일러스트 100개다.

측정 항목:

- Recall@K (K=1, 5, 10)
- MRR
- mAP
- 스타일별 성능
- category·색상·속성·재질 필터별 성능

## 7. REDTEAM 필수 점검

- 최종 metadata ID와 Vector DB payload ID가 1:1인지 확인
- split 간 ID 중복 0인지 확인
- 다른 스타일의 이미지가 잘못된 split에 들어가지 않았는지 확인
- 임베딩 파일의 행 수와 split 행 수가 같은지 확인
- 이미지 임베딩과 텍스트 임베딩의 차원·모델 버전이 같은지 확인
- cosine similarity 전에 벡터 정규화 여부를 통일
- 삭제·보류 에셋이 색인에 포함되지 않았는지 확인
- source/license payload 누락 0인지 확인
- 평가 정답 ID가 색인에 실제 존재하는지 확인

## 8. 데이터 담당에게 반환할 결과

백엔드는 다음 파일을 데이터 담당에게 전달한다.

- `model_info.json`
- 임베딩 생성 로그
- Vector DB collection/index 이름
- 색인된 에셋 수와 누락 ID 목록
- Recall@K, MRR, mAP 결과 JSON
- 오류·제외 에셋 목록

이 결과를 받은 뒤 데이터 담당이 최종 성능 보고서에 반영한다.
