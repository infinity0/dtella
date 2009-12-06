echo Collecting source code...

rmdir /s /q %BLDIR%/%FILEBASE%
del %BLDIR%/%FILEBASE%.tar
del %BLDIR%/%FILEBASE%.tar.bz2

mkdir %BLDIR%/%FILEBASE%
mkdir %BLDIR%/%FILEBASE%/dtella
mkdir %BLDIR%/%FILEBASE%/dtella/client
mkdir %BLDIR%/%FILEBASE%/dtella/common
mkdir %BLDIR%/%FILEBASE%/dtella/modules
mkdir %BLDIR%/%FILEBASE%/docs

copy dtella.py                %BLDIR%\%FILEBASE%
copy dtella\__init__.py       %BLDIR%\%FILEBASE%\dtella
copy dtella\local_config.py   %BLDIR%\%FILEBASE%\dtella
copy dtella\client\*.py       %BLDIR%\%FILEBASE%\dtella\client
copy dtella\common\*.py       %BLDIR%\%FILEBASE%\dtella\common
copy dtella\modules\*.py      %BLDIR%\%FILEBASE%\dtella\modules
copy docs\readme.txt          %BLDIR%\%FILEBASE%\docs
copy docs\changelog.txt       %BLDIR%\%FILEBASE%\docs
copy docs\changelog_adc.txt   %BLDIR%\%FILEBASE%\docs
copy docs\requirements.txt    %BLDIR%\%FILEBASE%\docs
copy docs\gpl.txt             %BLDIR%\%FILEBASE%\docs

pushd %BLDIR%

IF EXIST %ARC% (%ARC% a -ttar %FILEBASE%.tar %FILEBASE%) ELSE (%ARC64% a -ttar %FILEBASE%.tar %FILEBASE%)
IF EXIST %ARC% (%ARC% a -tbzip2 %FILEBASE%.tar.bz2 %FILEBASE%.tar) ELSE (%ARC64% a -tbzip2 %FILEBASE%.tar.bz2 %FILEBASE%.tar)

del %FILEBASE%.tar
rmdir /s /q %FILEBASE%
popd
