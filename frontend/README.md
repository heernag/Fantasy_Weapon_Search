# Fantasy Weapon Search (공개 검색 사이트)

이 폴더만 공개 배포합니다. 로컬 관리자 성능평가 화면은 별도 [admin-dashboard](../admin-dashboard/README.md) 앱으로 분리되어 있으며, 이 공개 앱에는 관리자 페이지와 평가 API 프록시가 포함되지 않습니다.

2D 판타지 무기 에셋을 이미지와 자연어 조건으로 탐색하는 멀티모달 검색 서비스의 프론트엔드입니다. FastAPI 검색 서버와 실제 데이터셋을 연결해 결과·이미지·필터 메타데이터를 표시합니다.

## 주요 기능

- 자연어 검색과 예시 질의
- 참고 이미지 선택 UI 및 이미지·텍스트 가중치 조절
- 백엔드 `/filters` 기반의 동적 무기·색상·속성·재질·스타일 필터
- 실제 API 응답의 유사도·검색 근거·출처·라이선스 정보를 포함한 결과 그리드
- 에셋 상세 패널 및 유사 에셋 검색
- 백엔드 평가 요약 API를 표시하는 성능 평가 화면
- 로딩, 오류, 빈 결과, 반응형 모바일 필터 상태

## 기술 구성

- Next.js 16
- React 19
- TypeScript
- CSS

## 실행 방법

Node.js 20 이상이 필요합니다.

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 엽니다.

PowerShell 실행 정책으로 `npm`이 동작하지 않으면 아래 명령을 사용합니다.

```powershell
npm.cmd install
npm.cmd run dev
```

프로덕션 빌드는 다음과 같이 확인합니다.

```bash
npm run build
```

## 프로젝트 구조

```text
app/
  page.tsx                 # 검색 및 성능 평가 화면
  globals.css              # 전역 스타일과 반응형 규칙
src/
  components/              # 필터, 결과 카드, 상세 패널, 평가 UI
  lib/searchService.ts     # FastAPI 호출 및 응답 변환
  lib/labels.ts            # API 값의 한국어 표시 레이블
  types/asset.ts           # 에셋·검색 요청·응답 타입
```

## 백엔드 연결

브라우저 요청은 Next.js의 `/api/backend/*` 프록시를 거쳐 FastAPI 서버로 전달됩니다. 기본 대상은 `http://127.0.0.1:8000`이며, 다른 주소를 쓸 때는 프런트엔드 실행 전 `BACKEND_API_BASE_URL`을 지정합니다.

```powershell
$env:BACKEND_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

텍스트는 `/search/text`, 이미지는 `/search/image`, 이미지+텍스트는 `/search/multimodal`로 자동 분기합니다. API가 제공하는 `top_k`와 `offset`으로 결과 페이지를 이동합니다.

## 현재 범위

- 백엔드 서버가 실행 중이어야 검색과 이미지 표시가 동작합니다.
- 성능 평가 화면은 /evaluation/summary의 실제 평가 세트 구성값을 표시합니다. Recall·MRR 같은 집계 지표는 별도 API가 추가되면 표시할 수 있습니다.
- API 키나 `.env` 파일은 GitHub에 커밋하지 않습니다.
