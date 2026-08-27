# Fantasy Weapon Search 관리자 대시보드

이 폴더는 공개 검색 사이트와 분리된 로컬 관리자 전용 프론트엔드입니다.

```bash
npm install
npm run dev
```

브라우저에서 `http://localhost:3001`을 엽니다. 백엔드가 기본 주소인 `http://127.0.0.1:8000`에서 실행 중이어야 합니다. 다른 백엔드를 사용할 경우 Git Bash에서 실행 전에 다음처럼 설정합니다.

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

이 앱은 배포 대상이 아닙니다. 공개 검색 사이트는 `../frontend` 폴더만 배포합니다.
