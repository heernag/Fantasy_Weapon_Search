$ErrorActionPreference = "Stop"

# 스크립트 위치를 기준으로 계산하므로 저장소가 다른 드라이브나 폴더로
# 복사되어도 호출한 사람의 현재 작업 디렉터리에 의존하지 않는다.
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "프로젝트 가상환경을 찾을 수 없습니다: $python"
}

# 사용자가 공용 캐시 위치를 이미 지정했다면 존중하고, 없을 때만 저장소 내부의
# 이동 가능한 기본 캐시를 사용한다. .cache는 Git에 포함되지 않는다.
if (-not $env:HF_HOME) {
    $env:HF_HOME = Join-Path $projectRoot ".cache\huggingface"
}
if (-not $env:TORCH_HOME) {
    $env:TORCH_HOME = Join-Path $projectRoot ".cache\torch"
}
if (-not $env:FWS_MODEL_CACHE) {
    $env:FWS_MODEL_CACHE = Join-Path $projectRoot ".cache\openclip"
}

# uvicorn의 app.main import도 프로젝트 루트에서 수행되도록 위치를 잠시 바꾼다.
Push-Location $projectRoot
try {
    & $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
