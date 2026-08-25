# Fantasy Weapon Search 현재 작업 상태

## 2026-08-19 인수인계 계약 정렬

- 최종 계약 기준: `docs/CUSTOM_ADAPTER_HANDOFF_KO.md`, `docs/AI_SEARCH_API_HANDOFF_KO.md`
- `[num3].txt`는 과거 구현 기록이며 현재 계약으로 사용하지 않음
- FastAPI 실제 HTTP 런타임은 `app/`; 최종 모델·FAISS 검색 런타임은
  `src/retrieval/search_service_adapter.WeaponSearchService`
- 별도 HTTP 모델 서버 없이 공식 최종 서비스를 FastAPI 프로세스에서 시작 시
  한 번 로드하고 요청 간 재사용
- 검색 결과에 인수인계용 `image_path`와 프론트엔드용 `image_url`을 함께 반환
- 입력 계약 오류는 `400`, 결과·에셋 없음은 `404`, 업로드 크기는 `413`, MIME은
  `415`, 번역 실패는 `503`으로 고정
- 멀티모달 기본 가중치는 검증 결과에 맞춰 이미지 `0.4`, 텍스트 `0.6` 유지

최신 검증 결과: `pytest` 55개 통과, `compileall` 통과, `pip check` 통과.

## 2026-08-19 디자인 계약 정렬

- 원래 디자인 필드 `color`, `element`, `handedness`, `style`, `source`를 공식 API에 반영
- 현재 확장 필드 `colors`, `elements`, `visual_style`, `primary_color`, `materials`, `shape_tags`, `source_url` 유지
- 같은 의미의 원래·확장 필드가 충돌하면 인수인계 계약에 따라 `400` 반환
- 이미지 검색 결과에 대표 텍스트 `result_text` 추가
- 별도 HTTP 모델 서버 대신 공식 `WeaponSearchService`를 직접 사용하고
  `app/official_search.py`는 HTTP 응답·로그 변환만 담당
- 기존 엔드포인트, 이미지 결과, FAISS 인덱스와 메타데이터 저장 형식 유지

당시 회귀 검증: `pytest` 52개 통과. 최신 결과는 위 인수인계 계약 정렬 절을 따른다.

---

- 기준일: 2026-08-19
- 데이터 상태: **freeze 가능**
- 전체 상태: **데이터·최종 모델·검색 백엔드 통합 완료, 프론트엔드 통합 진행 필요**

| 항목 | 상태 | 결과 |
| --- | --- | --- |
| 최종 메타데이터 | 완료 | 1,391개 |
| 스타일 분리 | 완료 | 픽셀아트 957, 일러스트 284, 렌더 아이콘 150 |
| split | 완료 | 픽셀아트 772/94/91, 일러스트 229/18/37, 렌더 아이콘 121/15/14 |
| 평가 세트 | 완료 | 텍스트 160, 이미지+문장 80, 일러스트 100 질의 |
| release manifest·handoff | 완료 | 현재 메타데이터와 split 해시 기준으로 생성 |
| 베이스 임베딩 | 완료 | OpenCLIP ViT-B-16, 1,391개 × 512차원 |
| 커스텀 어댑터 | 완료 | 동결 OpenCLIP 인코더 + 이미지·텍스트 residual adapter, best epoch 8 |
| adapter 임베딩 | 완료 | 1,391개 × 512차원, 모델 정보와 asset_id 저장 |
| 모델 검증 | 완료 | validation mean Recall@5 0.771277 → 0.941490 |
| 멀티모달 평가 | 완료 | 최적 가중치 이미지 0.4 / 텍스트 0.6, test Recall@5 0.500 |
| 백엔드 API | 완료 | 텍스트·이미지·멀티모달 검색, 필터, 상세 조회, 로그 |
| 자동 검증 | 통과 | `tests/` 55개 통과, compileall 및 pip check 통과 |
| adapter API 연결 | 완료 | ViT-B-16 residual adapter와 동일 임베딩의 FAISS 인덱스 연결 |
| 최종 API 계약 | 완료 | 9개 필터 AND, GET/POST 텍스트 검색, 한국어 번역, 자기 자신 제외, 인수인계 상태 코드 적용 |
| 서비스 manifest | 완료 | 모델·adapter·임베딩·메타데이터·FAISS SHA-256 시작 시 검증 |
| 응답시간·CORS | 완료 | 전체/내부 검색시간 분리, 명시적 origin만 CORS 허용 |
| 프론트엔드 통합 | 진행 필요 | 검색 UI와 실제 API 연동·통합 시연 필요 |

## 다음 핵심 단계

1. 프론트엔드 검색 화면에서 실제 API를 호출하는 통합 시험을 수행한다.
2. 배포 환경에 OpenCLIP·번역 모델 캐시를 마운트한다.
3. 최종 시연·발표 자료를 준비한다.
