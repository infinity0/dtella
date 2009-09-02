set BLDIR="installer_win"
set ARC="C:\Program Files\7-Zip\7z.exe"
set ARC64="C:\Program Files (x86)\7-Zip\7z.exe"
set NSIS="C:\Program Files\NSIS\makensis.exe"
set NSIS64="C:\Program Files (x86)\NSIS\makensisw.exe"
set PYTHON="C:\python26\python.exe"
set OUTDIR="dist"

echo Now Checking for Build Utilities...

IF EXIST %PYTHON% (echo Found Python...) ELSE (
echo ERROR: Python Not Found.
pause
EXIT
)

IF EXIST %ARC% (echo Found 7-Zip Archiver...) ELSE (
IF EXIST %ARC64% (echo Found 7-Zip Archiver...) ELSE (
echo ERROR: 7-Zip Archiver Not Found.
pause
EXIT
) )

IF EXIST %NSIS% (echo Found NSIS compiler...) ELSE (
IF EXIST %NSIS64% (echo Found NSIS compiler...) ELSE (
echo ERROR: NSIS Compiler Not Found.
pause
EXIT
) )
echo All Dependencies Found, continuing...
