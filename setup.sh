#!/usr/bin/env bash
# ============================================================
# Mad Makers — setup collaborateur (Linux/Mac/Git Bash sur Windows)
# ============================================================
set -e

cd "$(dirname "$0")"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Mad Makers — Setup CRM (collaborateur)"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Check Python ──────────────────────────────────────────────
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python non trouvé. Installe Python 3.11+ depuis python.org"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
echo "✓ Python : $($PYTHON --version)"

# ── Install deps ──────────────────────────────────────────────
echo ""
echo "→ Installation des dépendances..."
$PYTHON -m pip install --upgrade pip --quiet
$PYTHON -m pip install -r crm/requirements.txt --quiet
$PYTHON -m pip install requests --quiet
echo "✓ Dépendances installées"

# ── Vérif présence des CSVs ───────────────────────────────────
echo ""
INPUTS_DIR="linkedin-scraper/data/inputs"
CSV_COUNT=$(ls "$INPUTS_DIR"/rocketreach_bulk_*.csv 2>/dev/null | wc -l)

if [ "$CSV_COUNT" -eq 0 ]; then
    echo "⚠️  Aucun CSV RocketReach trouvé dans $INPUTS_DIR/"
    echo ""
    echo "   Demande à Maïck le lien Google Drive / WeTransfer privé"
    echo "   contenant les fichiers :"
    echo "     - rocketreach_bulk_100_*.csv"
    echo "     - rocketreach_bulk_101-200_*.csv"
    echo "     - rocketreach_bulk_201-300_*.csv"
    echo "     - rocketreach_bulk_301-400_*.csv"
    echo "     - rocketreach_bulk_401-500_*.csv"
    echo "     - prospects_triage_strict_*_recheck.csv (à placer dans linkedin-scraper/data/)"
    echo ""
    echo "   Puis relance ce script."
    exit 1
fi

echo "✓ $CSV_COUNT CSVs RocketReach trouvés"

# ── Vérif CSV triage ──────────────────────────────────────────
TRIAGE_CSV=$(ls linkedin-scraper/data/prospects_triage_strict_*_recheck.csv 2>/dev/null | head -1)
if [ -z "$TRIAGE_CSV" ]; then
    TRIAGE_CSV=$(ls linkedin-scraper/data/prospects_triage_final_*.csv 2>/dev/null | head -1)
fi
if [ -z "$TRIAGE_CSV" ]; then
    echo "⚠️  Pas de CSV triage final trouvé. Lancement du pipeline triage..."
    cd linkedin-scraper
    $PYTHON -X utf8 scripts/triage_sites.py
    $PYTHON -X utf8 scripts/reclassify_triage.py
    $PYTHON -X utf8 scripts/triage_recheck.py
    cd ..
    TRIAGE_CSV=$(ls linkedin-scraper/data/prospects_triage_strict_*_recheck.csv 2>/dev/null | head -1)
fi
echo "✓ CSV triage : $(basename "$TRIAGE_CSV")"

# ── Import dans le CRM ────────────────────────────────────────
echo ""
echo "→ Import des prospects dans le CRM SQLite..."
$PYTHON -X utf8 -m crm.import_prospects --csv "$TRIAGE_CSV"

# ── Enrichissement phones ─────────────────────────────────────
echo ""
echo "→ Enrichissement avec les téléphones (depuis RocketReach raw)..."
$PYTHON -X utf8 -m crm.enrich_phones

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ Setup terminé."
echo ""
echo "  Lance le CRM avec :"
echo "    python -X utf8 -m crm.run"
echo ""
echo "  Puis ouvre http://127.0.0.1:8000"
echo "════════════════════════════════════════════════════════════"
