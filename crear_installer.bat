@echo off
:: Ruta del script (sin barra final)
SET CURRENT_DIR=%~dp0
SET CURRENT_DIR=%CURRENT_DIR:~0,-1%

:: Definir carpeta de aje-libs (hermana de la actual)
pushd "%CURRENT_DIR%\..\aje-libs"
SET AJELIB_DIR=%CD%
popd

echo ===================================
echo Generador de .whl para aje_libs
echo ===================================
echo.

:: Confirmación del usuario
echo Se generará un archivo .whl desde la carpeta:
echo  %AJELIB_DIR%
echo El .whl se guardará en:
echo  %CURRENT_DIR%\installer_aje_libs
echo.
set /p CONFIRM=¿Desea continuar? (S/N): 
if /i not "%CONFIRM%"=="S" goto :EOF

:: Crear entorno virtual
echo.
echo Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate.bat

:: Actualizar pip
echo.
echo Actualizando pip...
python -m pip install --upgrade pip

:: Generar el .whl de aje_libs
call :build_whl_layer "installer_aje_libs" "%AJELIB_DIR%"

:: Desactivar entorno virtual
call venv\Scripts\deactivate.bat

:: Mensaje final
echo.
echo ===================================
echo Proceso completado
echo ===================================
echo.
echo .whl generado en: %CURRENT_DIR%\installer_aje_libs
echo.
pause > nul
goto :eof

:: ===================================
:: Función: build_whl_layer
:: ===================================
:build_whl_layer
SETLOCAL
set LAYER_NAME=%~1
set SOURCE_DIR=%~2
set TARGET_DIR=%CURRENT_DIR%\%LAYER_NAME%
echo.
echo ===================================
echo Generando .whl para %LAYER_NAME%
echo ===================================

if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
mkdir "%TARGET_DIR%"

:: Entrar al directorio de origen
pushd "%SOURCE_DIR%"

:: Instalar build si es necesario
pip install --quiet build >nul

:: Limpiar builds anteriores
rmdir /S /Q dist 2>nul
rmdir /S /Q build 2>nul
for /D %%i in (*.egg-info) do rmdir /S /Q "%%i" 2>nul

:: Ejecutar build
python -m build --wheel

:: Mover el .whl al destino
move dist\*.whl "%TARGET_DIR%" >nul

popd

echo .whl generado en: %TARGET_DIR%
ENDLOCAL
goto :eof
