# Arcane Arsenal Frontend

2D 판타지 무기 에셋을 이미지와 자연어 조건으로 탐색하는 멀티모달 검색 서비스의 프론트엔드입니다. 현재는 백엔드와 실제 데이터셋 연결 전 단계로, 목데이터를 이용해 검색 경험과 발표용 성능 평가 화면을 구현합니다.

## 주요 기능

- 자연어 검색과 예시 질의
- 참고 이미지 선택 UI 및 이미지·텍스트 가중치 조절
- 무기 종류, 색상, 속성, 스타일, 형태, 희귀도 필터
- 유사도·일치 근거·출처·라이선스 정보를 포함한 결과 그리드
- 에셋 상세 패널 및 유사 에셋 검색
- 기준 모델과 재정렬 모델을 비교하는 성능 평가 대시보드
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
  data/mockAssets.ts       # 발표용 무기 목데이터
  lib/searchService.ts     # 현재 목데이터 검색, 이후 API 연결 지점
  types/asset.ts           # 에셋·검색 요청·응답 타입
```

## 백엔드 연결

화면 컴포넌트는 백엔드를 직접 호출하지 않습니다. 백엔드가 준비되면 `src/lib/searchService.ts`의 `searchAssets()` 내부를 FastAPI 검색 API 호출로 교체하면 됩니다.

예상 요청 값은 검색어, 이미지 파일, 이미지 가중치, 필터, 정렬 기준입니다. 응답에는 최소한 에셋 ID, 이름, 이미지 URL, 유사도, 일치 근거, 무기 메타데이터, 출처, 제작자, 라이선스가 포함되어야 합니다.

## 현재 범위

- 실제 데이터베이스, 벡터 검색, LLM API, 이미지 서버는 포함하지 않습니다.
- 검색 결과와 성능 지표는 UI 시연용 목데이터입니다.
- API 키나 `.env` 파일은 GitHub에 커밋하지 않습니다.
