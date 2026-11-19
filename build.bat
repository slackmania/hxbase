@echo off
REM HxBase build: .prg forras -> onallo, mindent tartalmazo .exe
REM Hasznalat: build.bat forras.prg [kimenet.exe]
REM Pelda:     build.bat examples\teszt50.prg
REM            build.bat examples\teszt50.prg dist\teszt50.exe
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Hasznalat: build.bat forras.prg [kimenet.exe]
  exit /b 1
)
set SRC=%~1
if not exist "%SRC%" (
  echo Nem talalhato: %SRC%
  exit /b 1
)
if "%~2"=="" (
  set OUT=dist\%~n1.exe
) else (
  set OUT=%~2
)
echo Forras: %SRC%
echo Kimenet: %OUT%
python -m hxbase build "%SRC%" -o "%OUT%"
if errorlevel 1 (
  echo BUILD HIBA
  exit /b 1
)
echo.
echo KESZ: %OUT%
endlocal
