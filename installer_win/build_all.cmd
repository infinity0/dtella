@echo off

REM This is a unified build script for building multiple "editions" of dtella.
REM
REM Usage: installer_win\build_all.cmd %BUILD_NAME% %INSTALL_TEMPLATE% %OUTTYPE% [%OUTFILE2%]

REM ----- DEPENDENCY CHECK ------
call installer_win\check_build_deps

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
call installer_win\build_source

REM ------- EXE -------------
echo Building Windows binary files...

call installer_win\build_py2exe %1
copy dist\dtella.exe %BLDIR%
copy dist\msvcr71.dll %BLDIR%

REM ------- DOCS ------------

copy docs\readme.txt %BLDIR%
copy docs\changelog.txt %BLDIR%
copy docs\changelog_adc.txt %BLDIR%


REM ------- INSTALLER -------
echo Building the installer...
pushd %BLDIR%

IF EXIST %NSIS% (%NSIS% %2) ELSE (%NSIS64% %2)

echo The build process is now complete!
popd

pause



REM -----CLEAN UP OUTPUT------

mkdir %OUTDIR%

move %BLDIR%\%FILEBASE%.%3 %OUTDIR%
IF !%4==! ( ) else ( move %BLDIR%\%4 %OUTDIR% )
move %BLDIR%\%FILEBASE%.tar.* %OUTDIR%


del %BLDIR%\msvcr71.dll
del %BLDIR%\readme.txt
del %BLDIR%\changelog.txt
del %BLDIR%\changelog_adc.txt
del %BLDIR%\dtella.exe
del %BLDIR%\%2
