@echo off
rem Compila "MicroGrano Lab.exe" con el compilador de C# incluido en Windows (.NET Framework 4).
rem No requiere instalar nada. El ejecutable queda en la raiz del repositorio.
setlocal
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo No se encontro csc.exe de .NET Framework 4.
  exit /b 1
)
"%CSC%" /nologo /codepage:65001 /target:winexe /optimize+ /platform:anycpu ^
  /win32icon:"%~dp0recursos\micrograno.ico" ^
  /win32manifest:"%~dp0MicroGranoLab.manifest" ^
  /reference:System.Windows.Forms.dll ^
  /out:"%~dp0..\MicroGrano Lab.exe" "%~dp0MicroGranoLab.cs"
if errorlevel 1 exit /b 1
echo Compilado: "%~dp0..\MicroGrano Lab.exe"
exit /b 0
