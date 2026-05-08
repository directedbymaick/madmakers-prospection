@echo off
REM ============================================================
REM Mad Makers — setup collaborateur (Windows cmd)
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   Mad Makers — Setup CRM (collaborateur)
echo ============================================================
echo.

REM ── Check Python ─────────────────────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo ERREUR : Python non trouve. Installe Python 3.11+ depuis python.org
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version') do echo OK Python : %%V

REM ── Install deps ─────────────────────────────────────────────
echo.
echo --^> Installation des dependances...
python -m pip install --upgrade pip --quiet
python -m pip install -r crm\requirements.txt --quiet
python -m pip install requests --quiet
echo OK Dependances installees

REM ── Verif CSVs RocketReach ───────────────────────────────────
echo.
set CSV_FOUND=0
for %%F in (linkedin-scraper\data\inputs\rocketreach_bulk_*.csv) do (
    set /a CSV_FOUND+=1
)

if !CSV_FOUND! EQU 0 (
    echo ATTENTION : Aucun CSV RocketReach trouve dans linkedin-scraper\data\inputs\
    echo.
    echo Demande a Maick le lien Google Drive / WeTransfer prive
    echo contenant les fichiers rocketreach_bulk_*.csv
    echo + le CSV triage prospects_triage_strict_*_recheck.csv
    echo.
    echo Place-les dans les bons dossiers puis relance ce script.
    exit /b 1
)
echo OK !CSV_FOUND! CSVs RocketReach trouves

REM ── Verif CSV triage final ───────────────────────────────────
set TRIAGE_CSV=
for /f "delims=" %%F in ('dir /b /o-d linkedin-scraper\data\prospects_triage_strict_*_recheck.csv 2^>nul') do (
    if not defined TRIAGE_CSV set TRIAGE_CSV=linkedin-scraper\data\%%F
)
if not defined TRIAGE_CSV (
    for /f "delims=" %%F in ('dir /b /o-d linkedin-scraper\data\prospects_triage_final_*.csv 2^>nul') do (
        if not defined TRIAGE_CSV set TRIAGE_CSV=linkedin-scraper\data\%%F
    )
)

if not defined TRIAGE_CSV (
    echo ATTENTION : Pas de CSV triage trouve. Lancement du pipeline triage...
    pushd linkedin-scraper
    python -X utf8 scripts\triage_sites.py
    python -X utf8 scripts\reclassify_triage.py
    python -X utf8 scripts\triage_recheck.py
    popd
    for /f "delims=" %%F in ('dir /b /o-d linkedin-scraper\data\prospects_triage_strict_*_recheck.csv 2^>nul') do (
        if not defined TRIAGE_CSV set TRIAGE_CSV=linkedin-scraper\data\%%F
    )
)
echo OK CSV triage : !TRIAGE_CSV!

REM ── Import CRM ───────────────────────────────────────────────
echo.
echo --^> Import des prospects dans le CRM SQLite...
python -X utf8 -m crm.import_prospects --csv "!TRIAGE_CSV!"

REM ── Enrich phones ────────────────────────────────────────────
echo.
echo --^> Enrichissement avec les telephones...
python -X utf8 -m crm.enrich_phones

echo.
echo ============================================================
echo   OK Setup termine.
echo.
echo   Lance le CRM avec :
echo     python -X utf8 -m crm.run
echo.
echo   Puis ouvre http://127.0.0.1:8000
echo ============================================================
endlocal
