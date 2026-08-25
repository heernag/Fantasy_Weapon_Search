# 판타지 무기 검색 사이트 데이터 연동 보고서

## 1. 보고서 목적

본 보고서는 [Arcane 검색 사이트](https://arcane-3463.vercel.app/)에 판타지 무기 이미지와 정리된 메타데이터를 연결하는 방법을 설명한다.

현재 데이터는 이미지 파일과 검색용 메타데이터가 연결된 상태이며, 사이트에서는 이를 이용해 무기 종류·색상·재질·속성·자연어 문장으로 검색할 수 있다.

## 2. 연동 대상 데이터

| 구분 | 위치 | 용도 |
|---|---|---|
| 픽셀아트 이미지 | `data/processed/pixel_art` | 픽셀아트 검색 결과 |
| 일러스트 이미지 | `data/processed/illustration` | 렌더·일러스트 검색 결과 |
| 통합 메타데이터 | `data/metadata` | 이미지와 태그 연결 |
| 평가 데이터 | `data/evaluation` | 검색 성능 검증 |

검증된 일러스트 데이터는 이미지와 메타데이터가 `asset_id`를 기준으로 연결되며, 출처와 라이선스 정보도 함께 보존한다.

## 3. 메타데이터 연결 구조

사이트는 각 이미지의 `asset_id`를 기준으로 다음 정보를 불러온다.

```json
{
  "asset_id": "asset_001833",
  "image_path": "data/processed/illustration/asset_001833.png",
  "category": "sword",
  "subcategory": "curved_sword",
  "primary_color": "purple",
  "colors": ["purple", "red", "magenta", "black", "silver", "brown", "gold"],
  "materials": ["steel", "leather", "crystal", "gold", "bronze"],
  "elements": [],
  "handedness": "one_handed",
  "caption_en": "A fantasy curved sword with a purple flame-like blade, red and magenta crystal ornaments, a metal guard, and a brown grip",
  "caption_ko": "보라색 불꽃형 칼날에 붉은색과 자홍색 수정 장식, 금속 가드와 갈색 손잡이가 어우러진 판타지 곡검",
  "source": "...",
  "license": "..."
}
```

## 4. 검색 처리 방식

### 필터 검색

사용자가 색상이나 무기 종류를 선택하면 메타데이터의 다음 필드를 기준으로 필터링한다.

- 무기 종류: `category`, `subcategory`
- 색상: `primary_color`, `colors`
- 재질: `materials`
- 속성: `elements`
- 사용 방식: `handedness`
- 스타일: `visual_style`, `style_variant`

### 자연어 검색

사용자의 검색 문장과 `caption_en`, `caption_ko`, 태그를 비교해 관련도가 높은 이미지를 우선 표시한다.

예시:

- “보라색 곡검” → `subcategory=curved_sword`, `primary_color=purple`
- “강철과 가죽으로 된 단검” → `materials`에 `steel`, `leather` 포함
- “불 속성 무기” → `elements`에 `fire` 포함

### 이미지+문장 검색

기준 이미지를 선택한 뒤 “파란색으로 바꿔줘”, “불 속성으로 찾아줘”와 같은 문장을 추가하면 이미지 유사도와 문장 조건을 함께 적용한다.

## 5. 검색 결과에 표시할 정보

검색 결과 카드에는 다음 항목을 표시한다.

1. 무기 이미지
2. 한글 캡션
3. 무기 종류와 세부분류
4. 주요 색상과 전체 색상
5. 재질
6. 속성
7. 출처와 라이선스

출처와 라이선스는 검색용 태그와 별도로 표시해 데이터 사용 근거를 확인할 수 있도록 한다.

## 6. 사이트에 넣지 않는 파일

다음 파일은 최종 검색 데이터가 아니므로 배포 대상에서 제외한다.

- `data/review` 아래의 수동 검수용 파일
- `manual_overrides.json` 같은 내부 수정 기록
- 중간 변환·검증 로그
- 삭제 요청 또는 미승인 이미지

사이트에는 검증이 끝난 이미지, 최종 메타데이터, 검색 인덱스만 전달한다.

## 7. 연동 작업 순서

1. 최종 이미지 폴더를 사이트의 이미지 저장소에 연결한다.
2. 최종 메타데이터 JSON을 읽어 `asset_id`와 이미지 경로를 매칭한다.
3. 필터 검색용 태그 인덱스를 생성한다.
4. 한글·영문 캡션과 태그를 이용해 텍스트 임베딩을 생성한다.
5. 이미지 임베딩을 생성하고 텍스트 임베딩과 연결한다.
6. 검색 결과에 캡션·태그·출처·라이선스를 함께 반환한다.
7. 평가 세트로 검색 결과와 정답을 비교한다.

## 8. 팀에 설명할 한 문장

> 정제된 판타지 무기 이미지와 메타데이터를 사이트의 검색 인덱스에 연결해, 사용자가 무기 종류·색상·재질·속성·자연어 문장으로 원하는 무기를 찾을 수 있도록 구성한다.

## 9. 현재 데이터 검증 상태

- 일러스트 후보: 300개
- 검증 후 포함: 283개
- 제외: 17개
- 일러스트 메타데이터 행: 284개
- 출처·라이선스 누락: 0개
- 이미지 오류: 0개
- 인코딩 오류: 0개
- 분할 누수: 0개
