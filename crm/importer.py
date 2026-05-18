"""crm.importer — parse et import auto de prospects depuis fichiers uploadés.

Formats supportés :
- CSV (RocketReach raw, triage Mad Makers, ou format générique)
- XLSX (Excel)
- PDF (extraction texte → email/téléphone détectés via regex)
- MD / TXT (idem PDF)

Détection auto du format (RocketReach vs triage Mad Makers vs générique).
Retourne un summary structuré pour affichage UI.
"""
import csv
import io
import logging
import re
from typing import Optional

log = logging.getLogger(__name__)


# ─── Détection automatique du type de CSV ────────────────────


def detect_csv_type(headers: list[str]) -> str:
    """Identifie le format d'un CSV depuis ses headers."""
    h_set = {h.lower().strip() for h in headers}

    # RocketReach raw : colonnes "Input - Full Name", "Recommended Email", "Mobile Phone"
    if {"input - full name", "recommended email"}.issubset(h_set):
        return "rocketreach"
    if {"input - linkedin url", "employer"}.issubset(h_set):
        return "rocketreach"

    # ADEME RGE scraper (Carnet Plein®) : sortie de scrape_rge_ademe.py
    if "rge_qualifications" in h_set or ("siret" in h_set and "phone_office" in h_set):
        return "ademe_rge"

    # Triage Mad Makers : sortie de triage_recheck.py / triage_apply_manual.py
    if "categorie" in h_set and "nom_complet" in h_set and "veillot_signals" in h_set:
        return "madmakers_triage"

    # CRM export : sortie de l'app CRM
    if "stage" in h_set and "nom_complet" in h_set and "phone_mobile" in h_set:
        return "crm_export"

    # Fallback générique
    return "generic"


# ─── Mappings header → champ DB ──────────────────────────────


# RocketReach raw (5 CSVs sources Mad Makers)
ROCKETREACH_MAPPING = {
    "Input - Full Name":          "nom_complet",
    "Input - First Name":         "prenom",
    "Input - Last Name":          "nom",
    "First Name":                 "prenom",
    "Last Name":                  "nom",
    "Input - Current Title":      "titre",
    "Title":                      "titre",
    "Input - Current Employer":   "entreprise",
    "Employer":                   "entreprise",
    "Employer Domain":            "domaine",
    "Employer Website":           "site_url",
    "Input - Location":           "ville",
    "Location":                   "ville",
    "Recommended Email":          "email",
    "Recommended Work Email":     "email",
    "Input - LinkedIn URL":       "linkedin_url",
    "LinkedIn":                   "linkedin_url",
    "Input - Company LinkedIn URL": "entreprise_linkedin",
    "Employer LinkedIn":          "entreprise_linkedin",
    "Phone":                      "phone_mobile",
    "Mobile Phone":               "phone_mobile",
    "Office Phone":               "phone_office",
    "Other Phones":               "phone_other",
}

# ADEME RGE (sortie scrape_rge_ademe.py — Carnet Plein® sourcing)
# Note : le SIRET est stocké dans la colonne 'siret' (ajoutée par migration db.py)
ADEME_RGE_MAPPING = {
    "siret":              "siret",
    "nom_complet":        "nom_complet",
    "prenom":             "prenom",
    "nom":                "nom",
    "titre":              "titre",
    "entreprise":         "entreprise",
    "ville":              "ville",
    "email":              "email",
    "phone_office":       "phone_office",    # explicite : ces phones sont des fixes pro
    "site_url":           "site_url",
    "domaine":            "domaine",
    "linkedin_url":       "linkedin_url",
    "source":             "source",
    "categorie":          "categorie",
    "notes":              "notes",
}

# Triage Mad Makers (sortie pipeline triage_recheck)
MADMAKERS_TRIAGE_MAPPING = {
    "categorie":           "categorie",
    "prenom":              "prenom",
    "nom":                 "nom",
    "nom_complet":         "nom_complet",
    "titre":               "titre",
    "entreprise":          "entreprise",
    "domaine":             "domaine",
    "site_url":            "site_url",
    "email":               "email",
    "linkedin_url":        "linkedin_url",
    "entreprise_linkedin": "entreprise_linkedin",
    "ville":               "ville",
    "copyright_year":      "copyright_year",
    "veillot_signals":     "veillot_signals",
    "recent_signals":      "recent_signals",
    "fetch_error":         "fetch_error",
}

# Generic — best effort mapping (variations courantes)
GENERIC_MAPPING_FUZZY = [
    (["nom complet", "full name", "name"],           "nom_complet"),
    (["prénom", "prenom", "first name"],             "prenom"),
    (["nom", "last name"],                           "nom"),
    (["titre", "title", "job title", "poste"],       "titre"),
    (["entreprise", "company", "employer", "société"], "entreprise"),
    (["ville", "city", "location"],                  "ville"),
    (["email", "e-mail", "mail"],                    "email"),
    (["linkedin", "linkedin url"],                   "linkedin_url"),
    (["site", "site web", "website", "url"],         "site_url"),
    (["téléphone", "telephone", "phone", "mobile", "portable"], "phone_mobile"),
    (["tel bureau", "office", "fixe"],               "phone_office"),
]


def _build_generic_mapping(headers: list[str]) -> dict:
    """Mapping fuzzy pour CSVs génériques (Excel custom, etc.)."""
    mapping = {}
    for h in headers:
        h_norm = h.lower().strip()
        for keywords, field in GENERIC_MAPPING_FUZZY:
            if any(kw in h_norm for kw in keywords):
                mapping[h] = field
                break
    return mapping


# ─── Helpers phone normalization ──────────────────────────────


def _clean_phone(s: str) -> str:
    if not s:
        return ""
    s = s.strip().replace(" ", "").replace(".", "").replace("-", "")
    if not s:
        return ""
    if re.match(r"^0\d{9}$", s):
        return f"+33 {s[1]} {s[2:4]} {s[4:6]} {s[6:8]} {s[8:10]}"
    if re.match(r"^33\d{9}$", s):
        rest = s[2:]
        return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    if s.startswith("0033"):
        rest = s[4:]
        if len(rest) == 9:
            return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    if s.startswith("+33"):
        rest = s[3:]
        if len(rest) == 9:
            return f"+33 {rest[0]} {rest[1:3]} {rest[3:5]} {rest[5:7]} {rest[7:9]}"
    return s


# ─── Parsers par format ──────────────────────────────────────


def parse_csv(content: bytes, filename: str = "") -> dict:
    """Parse un CSV, retourne {rows: [...], format: str, headers: [...]}."""
    # Decode with BOM tolerance
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Impossible de décoder le CSV (encodage non supporté)")

    # Auto-detect delimiter
    sniffer = csv.Sniffer()
    sample = text[:4096]
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
    except csv.Error:
        # fallback default comma
        class _D:
            delimiter = ","
            quotechar = '"'
        dialect = _D()

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = list(reader)
    headers = reader.fieldnames or []

    fmt = detect_csv_type(headers)
    log.info(f"CSV parsed: {filename} — {len(rows)} rows, format={fmt}")

    return {"rows": rows, "format": fmt, "headers": headers}


def parse_xlsx(content: bytes, filename: str = "") -> dict:
    """Parse un fichier XLSX (1ère feuille uniquement, 1ère ligne = headers)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    try:
        headers_row = next(rows_iter)
    except StopIteration:
        return {"rows": [], "format": "empty", "headers": []}

    headers = [str(h).strip() if h is not None else "" for h in headers_row]
    rows = []
    for r in rows_iter:
        if not r or all(v is None for v in r):
            continue
        d = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            v = r[i] if i < len(r) else None
            d[h] = "" if v is None else str(v).strip()
        if d:
            rows.append(d)

    fmt = detect_csv_type(headers)
    log.info(f"XLSX parsed: {filename} — {len(rows)} rows, format={fmt}")
    return {"rows": rows, "format": fmt, "headers": headers}


# ─── Extracteur texte (PDF / MD / TXT) ───────────────────────


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+33|0033|0)\s?[1-9](?:[\s.-]?\d{2}){4}")
URL_RE = re.compile(r"https?://[^\s<>\"']+")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[A-Za-z0-9_-]+", re.I)


def parse_text_blob(content: bytes, filename: str = "") -> dict:
    """Parse PDF / MD / TXT — extrait emails, téléphones, URLs détectés."""
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode("utf-8", errors="ignore")

    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))
    phones = list(dict.fromkeys(PHONE_RE.findall(text)))
    urls = list(dict.fromkeys(URL_RE.findall(text)))
    linkedins = list(dict.fromkeys(("https://" + m) if not m.startswith("http") else m
                                    for m in LINKEDIN_RE.findall(text)))

    # Pour chaque email trouvé, créer une row "prospect" minimale
    rows = []
    for email in emails:
        rows.append({
            "email": email,
            "nom_complet": email.split("@")[0].replace(".", " ").title(),
            "entreprise": email.split("@")[1].split(".")[0].title(),
        })

    log.info(f"Text blob parsed: {filename} — {len(emails)} emails, {len(phones)} phones, {len(urls)} URLs")
    return {
        "rows": rows,
        "format": "text_extracted",
        "headers": ["email", "nom_complet", "entreprise"],
        "_extras": {"phones": phones, "urls": urls, "linkedins": linkedins},
    }


def parse_file(filename: str, content: bytes) -> dict:
    """Dispatch selon l'extension."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return parse_csv(content, filename)
    if name.endswith((".xlsx", ".xlsm")):
        return parse_xlsx(content, filename)
    if name.endswith((".pdf", ".md", ".txt")):
        return parse_text_blob(content, filename)
    raise ValueError(f"Format non supporté : {filename} (formats acceptés : csv, xlsx, pdf, md, txt)")


# ─── Mappage row brute → dict prospect prêt pour upsert ──────


def _apply_mapping(row: dict, mapping: dict) -> dict:
    """Convertit une row brute via un mapping {col_source → champ_db}."""
    out = {}
    for src, dst in mapping.items():
        val = row.get(src, "")
        if isinstance(val, str):
            val = val.strip()
        if val:
            out[dst] = val
    return out


def normalize_rows(parsed: dict) -> list[dict]:
    """Convertit les rows brutes en dicts prospects prêts pour upsert_prospect()."""
    fmt = parsed["format"]
    rows = parsed["rows"]

    if fmt == "rocketreach":
        mapping = ROCKETREACH_MAPPING
    elif fmt == "madmakers_triage":
        mapping = MADMAKERS_TRIAGE_MAPPING
    elif fmt == "ademe_rge":
        mapping = ADEME_RGE_MAPPING
    elif fmt == "crm_export":
        # CRM export : tous les headers sont déjà les champs DB
        mapping = {h: h for h in parsed.get("headers", [])}
    elif fmt == "text_extracted":
        # Déjà mappé dans parse_text_blob
        return rows
    else:
        mapping = _build_generic_mapping(parsed.get("headers", []))

    out = []
    for r in rows:
        d = _apply_mapping(r, mapping)
        if not d.get("nom_complet") and (d.get("prenom") or d.get("nom")):
            d["nom_complet"] = f"{d.get('prenom','')} {d.get('nom','')}".strip()
        if not d.get("nom_complet") and d.get("email"):
            d["nom_complet"] = d["email"].split("@")[0].replace(".", " ").title()
        # Normalise les téléphones
        for phk in ("phone_mobile", "phone_office", "phone_other"):
            if d.get(phk):
                d[phk] = _clean_phone(d[phk])
        # source par défaut
        if not d.get("source"):
            d["source"] = {
                "rocketreach":       "rocketreach",
                "madmakers_triage":  "triage_pipeline",
                "ademe_rge":         "ademe_rge",
                "crm_export":        "crm_export",
                "text_extracted":    "text_upload",
                "generic":           "csv_generic",
            }.get(fmt, "upload")
        # Catégorie : dérivée du site_url pour les imports ADEME RGE
        # (la colonne categorie n'est pas dans le CSV enrichi).
        # sans_site : pas de site → cible priorité Carnet Plein®
        # avec_site_veillot : a un site mais probablement à refaire
        # → on n'auto-classifie pas avec_site_recent ici (audit manuel requis)
        if fmt == "ademe_rge" and not d.get("categorie"):
            d["categorie"] = "avec_site_veillot" if d.get("site_url") else "sans_site"
        if d.get("nom_complet"):
            out.append(d)
    return out


def import_to_db(prospects: list[dict], user_id: int = None) -> dict:
    """Upserts les prospects, retourne stats."""
    from . import models as M

    inserted = 0
    updated = 0
    skipped = 0

    for p in prospects:
        if not p.get("nom_complet"):
            skipped += 1
            continue
        existing = None
        if p.get("entreprise"):
            from .db import query_one
            existing = query_one(
                "SELECT id FROM prospects WHERE nom_complet = ? AND entreprise = ?",
                (p["nom_complet"], p["entreprise"]),
            )
        if existing:
            updated += 1
        else:
            inserted += 1
        try:
            pid = M.upsert_prospect(p)
            if not existing:
                M.create_activity(
                    pid, "note",
                    f"Importé via UI — source : {p.get('source', 'upload')}",
                    f"Catégorie : {p.get('categorie', 'sans_site')}",
                    user_id=user_id,
                )
        except Exception as e:
            log.exception(f"upsert failed for {p.get('nom_complet')}: {e}")
            skipped += 1

    return {"inserted": inserted, "updated": updated, "skipped": skipped,
            "total": len(prospects)}
