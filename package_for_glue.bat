@echo off
SETLOCAL ENABLEEXTENSIONS

:: Script para empaquetar aje_libs para AWS Glue
:: Este script ejecuta package_for_glue.py (versión Python)
:: Para usar solo batch, ejecuta crear_glue_layer.bat

SET CURRENT_DIR=%~dp0
SET CURRENT_DIR=%CURRENT_DIR:~0,-1%

echo ===================================
echo Empaquetando aje_libs para AWS Glue
echo ===================================
echo.
echo Usando script Python...
echo (Para usar solo batch, ejecuta crear_glue_layer.bat)
echo.

:: Verificar que Python está disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está disponible en el PATH
    echo    Por favor, asegúrate de que Python esté instalado y en el PATH
    echo    O ejecuta crear_glue_layer.bat que no requiere Python
    pause
    exit /b 1
)

:: Ejecutar el script Python
python "%CURRENT_DIR%\package_for_glue.py"

if errorlevel 1 (
    echo.
    echo ❌ Error durante el empaquetado
    pause
    exit /b 1
)

echo.
echo ✅ Proceso completado
pause

