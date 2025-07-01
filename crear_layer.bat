@echo on
SETLOCAL ENABLEEXTENSIONS

:: Mostrar errores si algo sale mal
set ERR=0

:: Ruta actual
SET CURRENT_DIR=%~dp0
SET CURRENT_DIR=%CURRENT_DIR:~0,-1%

pushd "%CURRENT_DIR%\..\aje-libs"
SET AJELIB_DIR=%CD%
popd

SET PYTHON_VERSION=3.10

echo ===================================
echo AWS Lambda Layers Generator
echo ===================================

echo Este script generará los siguientes layers...
set /p CONFIRM=¿Desea continuar? (S/N): 
if /i not "%CONFIRM%"=="S" goto end

:: Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv || set ERR=1

call venv\Scripts\activate.bat || set ERR=1

:: Actualizar pip
python -m pip install --upgrade pip || set ERR=1

:: Crear layers
call :create_layer "layer_aje_libs" "%AJELIB_DIR%" || set ERR=1
call :create_layer "layer_pyodbc" "pyodbc>=4.0.39" || set ERR=1
call :create_layer "layer_docs" "python-docx>=0.8.11 python-pptx>=0.6.21 openpyxl>=3.1.0 PyPDF2>=3.0.0 lxml==4.9.2" || set ERR=1
call :create_layer "layer_pinecone" "pinecone>=2.2.0" || set ERR=1
call :create_layer "layer_requests" "requests>=2.31.0" || set ERR=1

call venv\Scripts\deactivate.bat

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
exit /b

:: Crear Layer
:create_layer
SETLOCAL
set LAYER_NAME=%~1
set DEPENDENCIES=%~2
set TARGET_DIR=%CURRENT_DIR%\%LAYER_NAME%

echo Creando %LAYER_NAME%...
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
mkdir "%TARGET_DIR%\python"

echo Instalando: %DEPENDENCIES%
pip install --no-cache-dir -t "%TARGET_DIR%\python" %DEPENDENCIES% || (echo ERROR al instalar %DEPENDENCIES% & ENDLOCAL & exit /b 1)

pushd "%TARGET_DIR%"
powershell Compress-Archive -Path "python" -DestinationPath "%TARGET_DIR%\%LAYER_NAME%.zip" -Force
popd

rmdir /s /q "%TARGET_DIR%\python"
echo %LAYER_NAME% creado: %TARGET_DIR%\%LAYER_NAME%.zip
ENDLOCAL
exit /b 0
