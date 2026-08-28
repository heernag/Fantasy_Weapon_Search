@echo off
setlocal

rem Always run from the repository root, even when this file is launched
rem by double-click or the repository is copied to another drive/folder.
pushd "%~dp0"

echo ============================================================
echo  Fantasy Weapon Search API
echo ============================================================
echo  Server URL : http://127.0.0.1:8000        (opens the API docs)
echo  Swagger UI : http://127.0.0.1:8000/docs
echo  Health     : http://127.0.0.1:8000/health
echo  Stop server: Press Ctrl+C
echo ------------------------------------------------------------
echo  This launcher preloads the Korean translation model before
echo  the server accepts requests (first Korean search stays fast).
echo  Startup takes a few seconds longer for this reason.
echo  Confirm with: curl http://127.0.0.1:8000/health
echo  Look for "translation_preloaded": true in the response.
echo ============================================================
echo.

rem The PowerShell script validates .venv, selects portable cache paths,
rem moves to the correct project root, and starts uvicorn.
rem
rem -Command is used on purpose instead of -File. With -File, powershell.exe
rem exits with 0 even when uvicorn fails, because a native command's exit code
rem is not a PowerShell terminating error and scripts/run_api.ps1 does not
rem forward it. The failure branch below would never run and the window would
rem close before the error could be read. "exit $LASTEXITCODE" forwards the
rem real exit code of uvicorn. Verified: uvicorn failure now reports 3, and a
rem missing .venv still reports a non-zero code from the script's own throw.
rem
rem If scripts/run_api.ps1 is ever changed to end with "exit $LASTEXITCODE",
rem this line can go back to the simpler -File form.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0scripts\run_api.ps1'; exit $LASTEXITCODE"
set "server_exit_code=%ERRORLEVEL%"

popd

rem Normal shutdown. Ctrl+C leaves either 0 (uvicorn shuts down gracefully) or
rem the Windows control-C status 0xC000013A, neither of which is a failure.
if "%server_exit_code%"=="0" goto :finished
if "%server_exit_code%"=="-1073741510" goto :finished

echo.
echo ============================================================
echo  Server stopped with an error. Exit code: %server_exit_code%
echo ============================================================
echo  Most common causes:
echo.
echo   1. Port 8000 is already in use.
echo      Close the other server, or find it with:
echo        netstat -ano ^| findstr :8000
echo.
echo   2. The virtual environment is missing.
echo        py -3.11 -m venv .venv
echo        .venv\Scripts\python.exe -m pip install -r requirements.txt
echo      Do NOT install requirements-ai.txt here; it pins a different
echo      numpy and can break faiss and torch.
echo.
echo   3. Startup validation failed because the model bundle and the
echo      index no longer match. Rebuild the index with:
echo        .venv\Scripts\python.exe scripts\build_final_index.py
echo  The line printed just above this box is the error reported by
echo  scripts\run_api.ps1. Read it first; it names the exact problem.
echo ============================================================
echo.
pause

:finished
exit /b %server_exit_code%
