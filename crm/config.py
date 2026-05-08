"""crm.config — paths, constants, stages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "crm.db"
SCHEMA_PATH = ROOT / "schema.sql"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

# ── Pipeline stages (ordre = ordre du kanban) ──────────────────
STAGES = [
    ("a_contacter",  "À contacter",        "#6B7280"),
    ("email_envoye", "Email envoyé",       "#3B82F6"),
    ("en_relance",   "En relance",         "#8B5CF6"),
    ("rdv_1_cale",   "RDV 1 calé",         "#F59E0B"),
    ("rdv_1_fait",   "RDV 1 fait",         "#FBBF24"),
    ("rdv_2_cale",   "RDV 2 calé",         "#EA580C"),
    ("rdv_2_fait",   "RDV 2 fait",         "#FB923C"),
    ("devis_envoye", "Devis envoyé",       "#0EA5E9"),
    ("signe",        "Signé",              "#22C55E"),
    ("perdu",        "Perdu",              "#EF4444"),
    ("dormant",      "Dormant",            "#6B7280"),
]
STAGE_KEYS = [s[0] for s in STAGES]
STAGE_LABELS = {k: v for k, v, _ in STAGES}
STAGE_COLORS = {k: c for k, _, c in STAGES}

# ── Catégories triage ──────────────────────────────────────────
CATEGORIES = {
    "sans_site":          ("SANS SITE",         "#991B1B", "#FEE2E2"),
    "avec_site_veillot":  ("VEILLOT",           "#92400E", "#FEF3C7"),
    "avec_site_recent":   ("RÉCENT",            "#3730A3", "#E0E7FF"),
}

# ── Activity types ─────────────────────────────────────────────
ACTIVITY_TYPES = {
    "call":         ("Cold call",     "#DC2626"),
    "email":        ("Email",          "#3B82F6"),
    "meeting":      ("Meeting / RDV",  "#F59E0B"),
    "note":         ("Note",           "#6B7280"),
    "stage_change": ("Changement stage","#8B5CF6"),
    "audit":        ("Audit site",     "#0EA5E9"),
    "task":         ("Tâche",          "#22C55E"),
}
