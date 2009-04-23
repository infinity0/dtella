@echo off

REM ----- DEPENDENCY CHECK ------
call check_build_deps

REM ----- SET FILEBASE -----
%PYTHON% makevars.py > makevars.bat
call makevars.bat
del makevars.bat
IF ()==(%FILEBASE%) (
echo ERROR: Could not generate FILEBASE.
pause
EXIT
)

REM ------- SOURCE CODE ---------
call build_source

REM ------- EXE -------------
echo Building Windows binary files...

call build_py2exe updater
copy dist\dtella.exe %BLDIR%
copy dist\msvcr71.dll %BLDIR%

REM ------- DOCS ------------

copy docs\readme.txt %BLDIR%
copy docs\changelog.txt %BLDIR%
copy docs\changelog_adc.txt %BLDIR%


REM ------- INSTALLER -------
echo Building the installer...
pushd %BLDIR%

IF EXIST %NSIS% (%NSIS% dtella_updater.nsi) ELSE (%NSIS64% dtella_updater.nsi)

echo The build process is now complete!
popd

pause



REM -----CLEAN UP OUTPUT------

mkdir %OUTDIR%

move %BLDIR%\%FILEBASE%.updater.exe %OUTDIR%
move %BLDIR%\%FILEBASE%.tar.* %OUTDIR%


del %BLDIR%\msvcr71.dll
del %BLDIR%\readme.txt
del %BLDIR%\changelog.txt
del %BLDIR%\changelog_adc.txt
del %BLDIR%\dtella.exe
del %BLDIR%\dtella_updater.nsi
