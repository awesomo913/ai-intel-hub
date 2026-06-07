@echo off
REM Build AIIntelHub.exe — run from the ai_intel_hub project directory
REM Output lands in dist\AIIntelHub.exe, then copied to Desktop\My Apps\

echo Building AIIntelHub.exe...

uv pip install pyinstaller --quiet

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name AIIntelHub ^
    --add-data "requirements.txt;." ^
    --add-data "%USERPROFILE%\.claude\scripts\crash_logger.py;." ^
    --hidden-import customtkinter ^
    --hidden-import feedparser ^
    --hidden-import bs4 ^
    --hidden-import PIL ^
    --hidden-import keyring ^
    --hidden-import fastapi ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import uvicorn.protocols.http.h11_impl ^
    --hidden-import uvicorn.protocols.websockets.websockets_impl ^
    --collect-all customtkinter ^
    run.py

if errorlevel 1 (
    echo BUILD FAILED — check output above
    pause
    exit /b 1
)

echo Copying to Desktop\My Apps...
if not exist "%USERPROFILE%\Desktop\My Apps" mkdir "%USERPROFILE%\Desktop\My Apps"
copy /Y dist\AIIntelHub.exe "%USERPROFILE%\Desktop\My Apps\AIIntelHub.exe"

echo Creating Desktop shortcut...
powershell -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%USERPROFILE%\Desktop\AIIntelHub.lnk'); $s.TargetPath='%USERPROFILE%\Desktop\My Apps\AIIntelHub.exe'; $s.Save()"

echo.
echo Done. AIIntelHub.exe is live at Desktop\My Apps\AIIntelHub.exe
