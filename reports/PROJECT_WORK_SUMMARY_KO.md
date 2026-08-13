# Fantasy Weapon Search 데이터 작업 요약

- 기준일: 2026-08-13
- 최종 에셋: 1,391개

## 완료

- 이미지·메타데이터 연결, 출처·라이선스, 태그 체계, 한글·영문 캡션 검수
- 스타일 분리: 픽셀아트 957개, 일러스트 284개, 렌더 아이콘 150개
- 유사 변형 그룹 기반 split과 텍스트·이미지+문장·일러스트 평가 정답 세트 재생성
- manifest, handoff, split/evaluation 요약 최신화

## 다음 담당 작업

백엔드·모델 담당자는 `handoff/backend_vector_db/`의 manifest와 split/evaluation 자료를 이용해 실제 CLIP 임베딩을 생성하고 검색 지표를 측정합니다.
