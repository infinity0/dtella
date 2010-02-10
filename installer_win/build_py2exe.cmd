@rem dist\dtella.exe --terminate

REM delete old directores
rmdir /s /q build
REM rmdir /s /q dist

%PYTHON% setup.py py2exe %1

if errorlevel 1 exit /b 1
pause
