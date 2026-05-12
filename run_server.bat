@echo off
cd /d E:\Fridge-Recipe-Maker-main\Fridge-Recipe-Maker-main
:loop
echo [%date% %time%] Starting server...
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 600
echo [%date% %time%] Server crashed! Restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
