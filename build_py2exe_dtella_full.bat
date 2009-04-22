@rem dist\dtella.exe --terminate

REM delete old directores
rmdir /s /q build
REM rmdir /s /q dist

c:\python25\python setup_dtella_full.py py2exe

pause