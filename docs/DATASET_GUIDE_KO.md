# 데이터셋 사용 안내

## 1. 파일 선택

- 전체 데이터를 살펴보거나 검색 인덱스를 만들 때는 `data/metadata/final_search_assets.jsonl`을 사용합니다.
- 사람이 내용을 읽고 검수할 때는 `data/metadata/final_search_assets_pretty.json`을 사용합니다.
- 모델을 학습할 때는 `data/splits/train.jsonl`을 사용합니다.
- 학습 도중 어떤 설정이 좋은지 비교할 때는 `data/splits/validation.jsonl`을 사용합니다.
- 모델 개발이 모두 끝난 후 마지막 점수를 측정할 때만 `data/splits/test.jsonl`을 사용합니다.

## 2. 이미지 열기

각 JSON 레코드의 `processed_file` 값은 이 패키지 폴더 기준 상대 경로입니다.

```python
import json
from pathlib import Path

project_root = Path(r"D:\Last_Team_Project_Fantasy_Weapon_Search")
metadata_path = project_root / "data" / "splits" / "train.jsonl"

records = [
    json.loads(line)
    for line in metadata_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

first_image = project_root / records[0]["processed_file"]
print(first_image)
```

## 3. 주요 검색 필드

- `caption_en`, `caption_ko`: 자연어 검색과 텍스트 임베딩
- `category`, `subcategory`: 무기 종류 검색
- `colors`, `primary_color`: 색상 검색
- `elements`: 불·얼음·신성 등 속성 검색
- `materials`: 강철·나무·청동 등 재질 검색
- `shape_tags`: 형태와 장식 검색
- `provenance`: 출처와 라이선스 확인

## 4. 주의사항

- `test.jsonl`을 학습이나 설정 선택에 사용하면 최종 평가 점수가 부정확해집니다.
- `ambiguous_archive` 출처는 라이선스 미확인이 아니라 동일 압축 원본 안에 대응 후보가 여러 개라는 뜻입니다.
- 외부 공개 전에는 `provenance`의 출처와 라이선스를 함께 제공하는 것이 좋습니다.
