# 백엔드·Vector DB 전달 자료

이 폴더는 최종 확정된 검색 데이터와 평가 파일을 백엔드·Vector DB 담당자에게 전달하기 위한 복사본입니다.

## 기준

- 기준 파일: `final_manifest.json`
- 메타데이터: 1,391개
- 픽셀아트: 957개
- 일러스트: 284개
- 렌더 아이콘: 150개

## 사용 순서

1. `final_manifest.json`의 상태와 SHA-256을 확인합니다.
2. `final_search_assets_pretty.json`을 이미지·메타데이터 매핑 기준으로 사용합니다.
3. `splits/`의 스타일별 train/validation/test를 임베딩 대상 목록으로 사용합니다.
4. `evaluation/`의 질의·정답 파일로 검색 성능을 측정합니다.
5. 실제 CLIP 임베딩을 생성한 뒤 Vector DB에 적재합니다.

`splits/pixel_art`, `splits/illustration`, `splits/rendered_icon`은 서로 독립적인 데이터셋입니다.
