@echo off
chcp 65001 >nul
echo ============================================
echo Installation du monitoring au démarrage
echo ============================================
echo.

set TASK_NAME=SiteMonitorService
set PYTHON=C:\laragon\bin\python\python-3.13\python.exe
set SCRIPT=C:\laragon\www\GBI\site_monitor\main.py
set DIR=C:\laragon\www\GBI\site_monitor

echo [1/3] Suppression de l'ancienne tâche...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
echo       OK

echo [2/3] Création de la nouvelle tâche...
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "cmd /c cd /d \"%DIR%\" && \"%PYTHON%\" \"%SCRIPT%\"" ^
    /sc ONSTART ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

if %errorlevel% equ 0 (
    echo       OK
) else (
    echo       ERREUR
    pause
    exit /b 1
)

echo [3/3] Démarrage du service...
schtasks /run /tn "%TASK_NAME%"
echo       OK

echo.
echo ============================================
echo ✅ INSTALLATION TERMINÉE AVEC SUCCÈS !
echo ============================================
echo.
echo Le monitoring est maintenant actif.
echo Il démarrera automatiquement au boot de Windows.
echo.
echo Commandes utiles :
echo   Vérifier l'état    : schtasks /query /tn "%TASK_NAME%"
echo   Arrêter            : schtasks /end /tn "%TASK_NAME%"
echo   Redémarrer         : schtasks /run /tn "%TASK_NAME%"
echo   Désinstaller       : schtasks /delete /tn "%TASK_NAME%" /f
echo.
echo Les logs sont dans : %DIR%\logs\
echo.
pause