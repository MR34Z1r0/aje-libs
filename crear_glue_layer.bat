@echo on
SETLOCAL ENABLEEXTENSIONS

:: Mostrar errores si algo sale mal
set ERR=0

:: Ruta actual (directorio donde está este script)
SET CURRENT_DIR=%~dp0
SET CURRENT_DIR=%CURRENT_DIR:~0,-1%

:: Ruta del código fuente
SET AJE_LIBS_SRC=%CURRENT_DIR%\src\aje_libs

:: Ruta de destino (proyecto CDK)
SET CDK_PROJECT_DIR=%CURRENT_DIR%\..\cdk-datalake-ingest-bigmagic
SET OUTPUT_DIR=%CDK_PROJECT_DIR%\artifacts\aws-glue\layer
SET OUTPUT_ZIP=%OUTPUT_DIR%\aje_libs.zip

echo ===================================
echo Generador de ZIP para AWS Glue
echo ===================================
echo.
echo Se generará un archivo ZIP desde:
echo  %AJE_LIBS_SRC%
echo.
echo El ZIP se guardará en:
echo  %OUTPUT_ZIP%
echo.
set /p CONFIRM=¿Desea continuar? (S/N): 
if /i not "%CONFIRM%"=="S" goto end

:: Verificar que existe el código fuente
if not exist "%AJE_LIBS_SRC%" (
    echo.
    echo ❌ Error: No se encontró el código fuente en: %AJE_LIBS_SRC%
    set ERR=1
    goto end
)

:: Crear directorio temporal
SET TEMP_DIR=%CURRENT_DIR%\temp_glue_package
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

:: Crear directorio de destino si no existe
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

:: Eliminar zip anterior si existe
if exist "%OUTPUT_ZIP%" (
    echo.
    echo 🗑️  Eliminando ZIP anterior...
    del /q "%OUTPUT_ZIP%"
)

echo.
echo ===================================
echo Copiando código fuente...
echo ===================================
xcopy /E /I /Y "%AJE_LIBS_SRC%" "%TEMP_DIR%\aje_libs\" >nul
if errorlevel 1 (
    echo ❌ Error al copiar código fuente
    set ERR=1
    goto cleanup
)

echo.
echo ===================================
echo Limpiando archivos innecesarios...
echo ===================================
:: Eliminar __pycache__
for /d /r "%TEMP_DIR%\aje_libs" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

:: Eliminar archivos .pyc, .pyo, .pyd
for /r "%TEMP_DIR%\aje_libs" %%f in (*.pyc *.pyo *.pyd) do @if exist "%%f" del /q "%%f" 2>nul

:: Eliminar .pytest_cache
for /d /r "%TEMP_DIR%\aje_libs" %%d in (.pytest_cache) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

:: Eliminar .mypy_cache
for /d /r "%TEMP_DIR%\aje_libs" %%d in (.mypy_cache) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

echo ✅ Archivos limpiados

echo.
echo ===================================
echo Creando archivo ZIP...
echo ===================================
pushd "%TEMP_DIR%"
powershell Compress-Archive -Path "aje_libs" -DestinationPath "%OUTPUT_ZIP%" -Force
if errorlevel 1 (
    echo ❌ Error al crear el ZIP
    set ERR=1
    popd
    goto cleanup
)
popd

:: Obtener tamaño del archivo
for %%A in ("%OUTPUT_ZIP%") do set ZIP_SIZE=%%~zA
set /a ZIP_SIZE_MB=%ZIP_SIZE% / 1048576

echo.
echo ===================================
echo ✅ Proceso completado
echo ===================================
echo.
echo 📦 Archivo: %OUTPUT_ZIP%
echo 📊 Tamaño: %ZIP_SIZE_MB% MB
echo.
echo 💡 Próximos pasos:
echo    1. El archivo está listo en: artifacts/aws-glue/layer/aje_libs.zip
echo    2. Al hacer 'cdk deploy', el archivo se subirá automáticamente a S3
echo    3. Los jobs de Glue lo usarán mediante --extra-py-files
echo.

goto cleanup

:cleanup
:: Limpiar directorio temporal
if exist "%TEMP_DIR%" (
    echo.
    echo 🧹 Limpiando directorio temporal...
    rmdir /s /q "%TEMP_DIR%"
)

:end
if %ERR% neq 0 (
    echo.
    echo ===============================
    echo ¡Hubo errores en el proceso!
    echo ===============================
) else (
    echo.
    echo ===============================
    echo Proceso completado correctamente.
    echo ===============================
)

echo.
echo Presione una tecla para salir...
pause >nul
exit /b %ERR%

