"""crm.models — query helpers for prospects, calls, activities, audits, emails."""
import json
from datetime import datetime
from .db import query, query_one, execute

# ── Prospects ─────────────────────────────────────────────────


def list_prospects(category=None, stage=None, search=None, ville=None, limit=None, order="updated_at DESC"):
    sql = "SELECT * FROM prospects WHERE 1=1"
    params = []
    if category:
        sql += " AND categorie = ?"; params.append(category)
    if stage:
        sql += " AND stage = ?"; params.append(stage)
    if ville:
        sql += " AND ville LIKE ?"; params.append(f"%{ville}%")
    if search:
        sql += " AND (nom_complet LIKE ? OR entreprise LIKE ? OR titre LIKE ? OR email LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    sql += f" ORDER BY {order}"
    if limit:
        sql += " LIMIT ?"; params.append(limit)
    return query(sql, params)


def search_prospects(filters: dict, *, sample_limit: int = 5) -> dict:
    """Recherche avancée multi-critères. Retourne {count, sample}.

    filters supportés (tous optionnels) :
      - categories: list[str]     ex: ["sans_site", "avec_site_veillot"]
      - stages:     list[str]
      - sources:    list[str]
      - villes:     list[str]     (LIKE %x%, OR entre les villes)
      - search:     str           (LIKE sur nom/entreprise/titre/email)
      - interest_min: int 1-5
      - interest_max: int 1-5
      - has_email:  bool
      - has_phone:  bool
      - has_site:   bool / None pour ne pas filtrer
      - last_contacted: 'never' / 'gt_7d' / 'gt_30d' / 'gt_90d' / 'lt_7d' / None
      - exclude_unsubscribed: bool (default True, RGPD)
      - exclude_in_campaign_id: int (exclut prospects déjà dans cette campagne)
      - exclude_in_other_campaigns: bool (exclut prospects déjà dans autres campagnes actives/draft)
      - order: 'name' / 'interest' / 'created' / 'updated'
    """
    where = ["1=1"]
    params = []

    cats = filters.get("categories") or []
    if cats:
        placeholders = ",".join(["?"] * len(cats))
        where.append(f"p.categorie IN ({placeholders})")
        params.extend(cats)

    stages = filters.get("stages") or []
    if stages:
        placeholders = ",".join(["?"] * len(stages))
        where.append(f"p.stage IN ({placeholders})")
        params.extend(stages)

    sources = filters.get("sources") or []
    if sources:
        placeholders = ",".join(["?"] * len(sources))
        where.append(f"p.source IN ({placeholders})")
        params.extend(sources)

    villes = filters.get("villes") or []
    if villes:
        ors = " OR ".join(["LOWER(p.ville) LIKE LOWER(?)"] * len(villes))
        where.append(f"({ors})")
        params.extend(f"%{v}%" for v in villes)

    search = (filters.get("search") or "").strip()
    if search:
        where.append("(p.nom_complet ILIKE ? OR p.entreprise ILIKE ? OR p.titre ILIKE ? OR p.email ILIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])

    imin = filters.get("interest_min")
    imax = filters.get("interest_max")
    if imin is not None:
        where.append("p.interet >= ?"); params.append(int(imin))
    if imax is not None:
        where.append("p.interet <= ?"); params.append(int(imax))

    if filters.get("has_email"):
        where.append("p.email IS NOT NULL AND p.email <> ''")
    if filters.get("has_phone"):
        where.append("(p.phone_mobile IS NOT NULL AND p.phone_mobile <> '') OR (p.phone_office IS NOT NULL AND p.phone_office <> '')")

    has_site = filters.get("has_site")
    if has_site is True:
        where.append("p.site_url IS NOT NULL AND p.site_url <> ''")
    elif has_site is False:
        where.append("(p.site_url IS NULL OR p.site_url = '')")

    lc = filters.get("last_contacted")
    if lc == "never":
        where.append("p.last_contacted_at IS NULL")
    elif lc == "gt_7d":
        where.append("(p.last_contacted_at IS NULL OR p.last_contacted_at < NOW() - INTERVAL '7 days')")
    elif lc == "gt_30d":
        where.append("(p.last_contacted_at IS NULL OR p.last_contacted_at < NOW() - INTERVAL '30 days')")
    elif lc == "gt_90d":
        where.append("(p.last_contacted_at IS NULL OR p.last_contacted_at < NOW() - INTERVAL '90 days')")
    elif lc == "lt_7d":
        where.append("p.last_contacted_at >= NOW() - INTERVAL '7 days'")

    if filters.get("exclude_unsubscribed", True):
        where.append("(p.email IS NULL OR p.email = '' OR NOT EXISTS (SELECT 1 FROM unsubscribes u WHERE LOWER(u.email) = LOWER(p.email)))")

    exc_cid = filters.get("exclude_in_campaign_id")
    if exc_cid:
        where.append("NOT EXISTS (SELECT 1 FROM campaign_targets t WHERE t.prospect_id = p.id AND t.campaign_id = ?)")
        params.append(int(exc_cid))

    if filters.get("exclude_in_other_campaigns"):
        where.append("""NOT EXISTS (
            SELECT 1 FROM campaign_targets t
            JOIN campaigns c ON c.id = t.campaign_id
            WHERE t.prospect_id = p.id
              AND c.status IN ('draft', 'active', 'paused')
              AND t.status = 'active'
        )""")

    where_clause = " AND ".join(where)

    # Count total
    count_sql = f"SELECT COUNT(*) AS n FROM prospects p WHERE {where_clause}"
    total = query_one(count_sql, params)["n"]

    # Sample
    order = filters.get("order") or "updated"
    order_sql = {
        "name":     "p.nom_complet ASC",
        "interest": "p.interet DESC NULLS LAST, p.updated_at DESC",
        "created":  "p.created_at DESC",
        "updated":  "p.updated_at DESC",
    }.get(order, "p.updated_at DESC")

    sample_sql = f"""
        SELECT p.id, p.nom_complet, p.entreprise, p.titre, p.ville, p.email,
               p.phone_mobile, p.phone_office, p.categorie, p.stage, p.interet,
               p.source, p.last_contacted_at, p.site_url
        FROM prospects p
        WHERE {where_clause}
        ORDER BY {order_sql}
        LIMIT ?
    """
    sample = query(sample_sql, params + [sample_limit])

    # Pour l'assign : liste des ids
    return {"count": total, "sample": sample, "where": where_clause, "params": params}


def search_prospect_ids(filters: dict) -> list[int]:
    """Retourne juste la liste des ids matchant les filtres (pour assign bulk)."""
    res = search_prospects(filters, sample_limit=0)
    where = res["where"]
    params = res["params"]
    rows = query(f"SELECT p.id FROM prospects p WHERE {where}", params)
    return [r["id"] for r in rows]


def get_prospect(prospect_id):
    return query_one("SELECT * FROM prospects WHERE id = ?", (prospect_id,))


def get_prospect_by_name(name):
    return query_one(
        "SELECT * FROM prospects WHERE LOWER(nom_complet) = LOWER(?)", (name,)
    )


def upsert_prospect(data):
    """Insert or update a prospect by nom_complet+entreprise. Returns id."""
    existing = query_one(
        "SELECT id FROM prospects WHERE nom_complet = ? AND entreprise = ?",
        (data.get("nom_complet"), data.get("entreprise")),
    )
    if existing:
        pid = existing["id"]
        update_prospect(pid, data)
        return pid
    fields = ["nom_complet", "prenom", "nom", "titre", "entreprise", "ville",
              "email", "linkedin_url", "entreprise_linkedin", "site_url",
              "domaine", "categorie", "veillot_signals", "recent_signals",
              "copyright_year", "fetch_error", "stage", "interet", "notes",
              "source"]
    cols, vals = [], []
    for f in fields:
        if f in data:
            cols.append(f); vals.append(data[f])
    sql = f"INSERT INTO prospects ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    return execute(sql, vals)


def update_prospect(prospect_id, fields):
    if not fields:
        return
    fields = dict(fields)
    fields["updated_at"] = datetime.utcnow().isoformat()
    cols = list(fields.keys())
    sql = f"UPDATE prospects SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?"
    execute(sql, list(fields.values()) + [prospect_id])


def update_stage(prospect_id, stage, note=None):
    """Update stage + log activity."""
    prev = get_prospect(prospect_id)
    update_prospect(prospect_id, {"stage": stage})
    create_activity(prospect_id, "stage_change",
                    f"Stage : {prev['stage']} → {stage}",
                    note or "")


# ── Audits ────────────────────────────────────────────────────


def latest_audit(prospect_id):
    return query_one(
        "SELECT * FROM audits WHERE prospect_id = ? ORDER BY created_at DESC LIMIT 1",
        (prospect_id,),
    )


def save_audit(prospect_id, audit_dict, user_id=None):
    raw = json.dumps(audit_dict, ensure_ascii=False)
    sql = """INSERT INTO audits (prospect_id, created_by_user_id, final_url, https, tls_version,
             security_grade, technos, veillot_tags, title, description, h1,
             copyright_year, html_size_kb, image_count, modern_image_count,
             findings, raw_data)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    return execute(sql, (
        prospect_id,
        user_id,
        audit_dict.get("final_url", ""),
        bool(audit_dict.get("https")),
        audit_dict.get("tls_version"),
        audit_dict.get("security_grade"),
        ", ".join(audit_dict.get("technos", []) or []),
        ", ".join(audit_dict.get("veillot_signals", []) or []),
        audit_dict.get("title", ""),
        audit_dict.get("description", ""),
        audit_dict.get("h1", ""),
        audit_dict.get("copyright_year"),
        audit_dict.get("html_size_kb"),
        audit_dict.get("image_count"),
        audit_dict.get("modern_image_count"),
        "\n".join(audit_dict.get("security_findings", []) or []),
        raw,
    ))


# ── Calls ─────────────────────────────────────────────────────


def list_calls(prospect_id):
    return query(
        "SELECT * FROM calls WHERE prospect_id = ? ORDER BY started_at DESC",
        (prospect_id,),
    )


def get_call(call_id):
    return query_one("SELECT * FROM calls WHERE id = ?", (call_id,))


def latest_call(prospect_id):
    return query_one(
        "SELECT * FROM calls WHERE prospect_id = ? ORDER BY started_at DESC LIMIT 1",
        (prospect_id,),
    )


def create_call(prospect_id, call_number=1, user_id=None):
    """Start a new call session — inserts a draft row, returns id."""
    return execute(
        "INSERT INTO calls (prospect_id, call_number, created_by_user_id) VALUES (?, ?, ?)",
        (prospect_id, call_number, user_id),
    )


def update_call(call_id, **fields):
    if not fields:
        return
    cols = list(fields.keys())
    sql = f"UPDATE calls SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?"
    execute(sql, list(fields.values()) + [call_id])


def complete_call(call_id, state, summary, statut, next_action,
                  rdv2_date, rdv2_heure, interet,
                  roi_valeur_client, roi_leads, roi_conversion, roi_devis,
                  visuels_promis=None, budget_recu=None):
    state_json = json.dumps(state, ensure_ascii=False)
    # Calc ROI
    gain = (roi_valeur_client or 0) * (roi_leads or 0) * ((roi_conversion or 0) / 100)
    payback = ((roi_devis or 0) / gain) if (gain > 0 and roi_devis) else None
    update_call(
        call_id,
        state=state_json, summary=summary, statut=statut,
        next_action=next_action,
        rdv2_date=rdv2_date, rdv2_heure=rdv2_heure, interet=interet,
        roi_valeur_client=roi_valeur_client, roi_leads=roi_leads,
        roi_conversion=roi_conversion, roi_devis=roi_devis,
        roi_gain_mensuel=gain or None,
        roi_payback_mois=payback,
        visuels_promis=visuels_promis, budget_recu=budget_recu,
        completed_at=datetime.utcnow().isoformat(),
    )


# ── Activities ────────────────────────────────────────────────


_USER_NAME_EXPR = (
    "COALESCE(NULLIF(u.full_name, ''), SPLIT_PART(u.email, '@', 1))"
)


def list_activities(prospect_id=None, limit=50):
    if prospect_id:
        return query(
            f"""SELECT a.*,
                       {_USER_NAME_EXPR} AS author_name,
                       u.email AS author_email
                FROM activities a
                LEFT JOIN users u ON u.id = a.created_by_user_id
                WHERE a.prospect_id = ?
                ORDER BY a.created_at DESC LIMIT ?""",
            (prospect_id, limit),
        )
    return query(
        f"""SELECT a.*,
                   p.nom_complet AS prospect_name,
                   p.entreprise  AS prospect_entreprise,
                   {_USER_NAME_EXPR} AS author_name,
                   u.email AS author_email
            FROM activities a
            LEFT JOIN prospects p ON p.id = a.prospect_id
            LEFT JOIN users u     ON u.id = a.created_by_user_id
            ORDER BY a.created_at DESC LIMIT ?""",
        (limit,),
    )


def list_due_activities(limit=20):
    """Activities with due_at <= now and not completed."""
    return query(
        f"""SELECT a.*,
                   p.nom_complet AS prospect_name,
                   p.entreprise  AS prospect_entreprise,
                   {_USER_NAME_EXPR} AS author_name,
                   u.email AS author_email
            FROM activities a
            LEFT JOIN prospects p ON p.id = a.prospect_id
            LEFT JOIN users u     ON u.id = a.created_by_user_id
            WHERE a.due_at IS NOT NULL AND a.completed_at IS NULL
            ORDER BY a.due_at ASC LIMIT ?""",
        (limit,),
    )


def create_activity(prospect_id, type_, title, body=None, due_at=None, metadata=None, user_id=None):
    return execute(
        """INSERT INTO activities (prospect_id, type, title, body, due_at, metadata, created_by_user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (prospect_id, type_, title, body or "", due_at,
         json.dumps(metadata, ensure_ascii=False) if metadata else None,
         user_id),
    )


def complete_activity(activity_id):
    execute(
        "UPDATE activities SET completed_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), activity_id),
    )


# ── Emails ────────────────────────────────────────────────────


def list_emails(prospect_id):
    return query(
        "SELECT * FROM emails WHERE prospect_id = ? ORDER BY created_at DESC",
        (prospect_id,),
    )


def create_email(prospect_id, sequence_step, subject, body, status="draft", scheduled_at=None):
    return execute(
        """INSERT INTO emails (prospect_id, sequence_step, subject, body, status, scheduled_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (prospect_id, sequence_step, subject, body, status, scheduled_at),
    )


def log_email_sent(*, prospect_id, user_id, from_email, from_name, to_email,
                   reply_to, subject, body, body_html,
                   resend_message_id=None, sequence_step="manual",
                   attachments_info=None, error=None, status="sent"):
    """Log un email envoyé (ou échoué) en DB. Retourne id."""
    sent_at = datetime.utcnow().isoformat() if status == "sent" else None
    return execute(
        """INSERT INTO emails
           (prospect_id, created_by_user_id, sequence_step,
            from_email, from_name, to_email, reply_to,
            subject, body, body_html, attachments_json,
            status, sent_at, resend_message_id, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (prospect_id, user_id, sequence_step,
         from_email, from_name, to_email, reply_to,
         subject, body, body_html,
         json.dumps(attachments_info, ensure_ascii=False) if attachments_info else None,
         status, sent_at, resend_message_id, error)
    )


# ─── Email Templates ─────────────────────────────────────────


SEGMENT_LABELS = {
    "A_SANS_SITE":  "Sans site",
    "B_DG":         "DG / Founder / CEO",
    "C_DAF":        "DAF / Finance",
    "D_MARKETING":  "Marketing / Growth",
    "E_RH":         "RH / Talent",
    "GENERIC":      "Générique",
}

STEP_LABELS = {
    "J0":     "J0 — Premier contact",
    "J+4":    "J+4 — Relance 1",
    "J+10":   "J+10 — Relance 2",
    "J+18":   "J+18 — Breakup",
    "custom": "Personnalisé",
}

CATEGORY_LABELS = {
    "cold_email":  "Cold email",
    "follow_up":   "Relance / Suivi",
    "breakup":     "Breakup",
    "rdv_recap":   "Récap RDV",
    "custom":      "Personnalisé",
}

# Variables exposées au template engine
TEMPLATE_VARIABLES = [
    ("prenom",       "Prénom du prospect"),
    ("nom",          "Nom de famille"),
    ("nom_complet",  "Nom complet"),
    ("titre",        "Titre / poste"),
    ("entreprise",   "Nom de l'entreprise"),
    ("ville",        "Ville"),
    ("email",        "Email du prospect"),
    ("site_url",     "URL du site web"),
    ("site_short",   "URL site (sans http/www)"),
    ("linkedin",     "LinkedIn du prospect"),
    ("user_prenom",  "Mon prénom (signataire)"),
    ("user_nom",     "Mon nom complet"),
    ("user_email",   "Mon email"),
    ("calendly",     "Lien Calendly Mad Makers"),
    ("today",        "Date du jour (JJ/MM/AAAA)"),
]


def list_templates(segment=None, step=None, include_archived=False):
    sql = "SELECT * FROM email_templates WHERE 1=1"
    params = []
    if not include_archived:
        sql += " AND is_archived = FALSE"
    if segment:
        sql += " AND segment = ?"; params.append(segment)
    if step:
        sql += " AND step = ?"; params.append(step)
    sql += " ORDER BY segment NULLS LAST, step NULLS LAST, name"
    return query(sql, params)


def get_template(tpl_id):
    return query_one("SELECT * FROM email_templates WHERE id = ?", (tpl_id,))


def create_template(*, name, subject, body_html, description="", category=None,
                    segment=None, step=None, user_id=None):
    return execute(
        """INSERT INTO email_templates
           (name, description, category, segment, step, subject, body_html, created_by_user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, category, segment, step, subject, body_html, user_id),
    )


def update_template(tpl_id, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    cols = list(fields.keys())
    sql = f"UPDATE email_templates SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?"
    execute(sql, list(fields.values()) + [tpl_id])


def archive_template(tpl_id):
    update_template(tpl_id, is_archived=True)


def delete_template(tpl_id):
    execute("DELETE FROM email_templates WHERE id = ?", (tpl_id,))


def render_template_for_prospect(tpl_dict: dict, prospect_dict: dict,
                                  current_user_dict: dict = None) -> dict:
    """Remplit les variables {{xxx}} avec les valeurs du prospect + user courant.

    Returns: {"subject": ..., "body_html": ...}
    """
    import re as _re
    from urllib.parse import urlparse

    p = prospect_dict or {}
    u = current_user_dict or {}

    # Build variables map
    site = (p.get("site_url") or "").strip()
    site_short = ""
    if site:
        try:
            parsed = urlparse(site if site.startswith("http") else "http://" + site)
            site_short = (parsed.netloc or parsed.path or "").lstrip("www.").rstrip("/")
        except Exception:
            site_short = site

    user_prenom = ""
    user_nom = u.get("full_name") or ""
    if user_nom:
        user_prenom = user_nom.split()[0]

    vars_map = {
        "prenom":       p.get("prenom") or (p.get("nom_complet") or "").split(" ")[0] or "",
        "nom":          p.get("nom") or "",
        "nom_complet":  p.get("nom_complet") or "",
        "titre":        p.get("titre") or "",
        "entreprise":   p.get("entreprise") or "",
        "ville":        p.get("ville") or "",
        "email":        p.get("email") or "",
        "site_url":     site,
        "site_short":   site_short,
        "linkedin":     p.get("linkedin_url") or "",
        "user_prenom":  user_prenom,
        "user_nom":     user_nom,
        "user_email":   u.get("email") or "",
        "calendly":     "https://calendly.com/directedbymaick/30min",
        "today":        datetime.now().strftime("%d/%m/%Y"),
    }

    def _render(text: str) -> str:
        if not text:
            return ""
        # {{var}} et {{ var }} (avec espaces autorisés)
        def repl(m):
            key = m.group(1).strip()
            return vars_map.get(key, m.group(0))
        return _re.sub(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}", repl, text)

    return {
        "subject":   _render(tpl_dict.get("subject", "")),
        "body_html": _render(tpl_dict.get("body_html", "")),
    }


# ─── Unsubscribes (RGPD) ─────────────────────────────────────


def is_unsubscribed(email: str) -> bool:
    if not email:
        return False
    row = query_one("SELECT id FROM unsubscribes WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    return bool(row)


def add_unsubscribe(email: str, prospect_id=None, reason: str = "", user_agent: str = ""):
    if not email:
        return None
    # UPSERT : si déjà désabonné, ne fait rien
    existing = query_one("SELECT id FROM unsubscribes WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    if existing:
        return existing["id"]
    return execute(
        """INSERT INTO unsubscribes (email, prospect_id, reason, user_agent)
           VALUES (?, ?, ?, ?)""",
        (email.strip().lower(), prospect_id, reason or "", user_agent or ""),
    )


def mark_email_sent(email_id):
    execute(
        "UPDATE emails SET status = 'sent', sent_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), email_id),
    )


# ── Statistics for dashboard ──────────────────────────────────


def stats_overview():
    """Return dict of dashboard stats."""
    total = query_one("SELECT COUNT(*) AS n FROM prospects")["n"]

    by_cat = {r["categorie"]: r["n"]
              for r in query("SELECT categorie, COUNT(*) AS n FROM prospects GROUP BY categorie")}
    by_stage = {r["stage"]: r["n"]
                for r in query("SELECT stage, COUNT(*) AS n FROM prospects GROUP BY stage")}

    calls_total = query_one("SELECT COUNT(*) AS n FROM calls WHERE completed_at IS NOT NULL")["n"]
    calls_week = query_one(
        """SELECT COUNT(*) AS n FROM calls
           WHERE completed_at IS NOT NULL
           AND completed_at >= NOW() - INTERVAL '7 days'"""
    )["n"]
    rdv2_count = query_one("SELECT COUNT(*) AS n FROM prospects WHERE stage = 'rdv_2_cale'")["n"]
    signed = query_one("SELECT COUNT(*) AS n FROM prospects WHERE stage = 'signe'")["n"]

    avg_payback = query_one(
        "SELECT AVG(roi_payback_mois) AS avg FROM calls WHERE roi_payback_mois IS NOT NULL"
    )
    avg_payback = avg_payback["avg"] if avg_payback else None

    due_today = query_one(
        """SELECT COUNT(*) AS n FROM activities
           WHERE due_at IS NOT NULL AND completed_at IS NULL
           AND due_at::date <= CURRENT_DATE"""
    )["n"]

    return {
        "total":        total,
        "by_cat":       by_cat,
        "by_stage":     by_stage,
        "calls_total":  calls_total,
        "calls_week":   calls_week,
        "rdv2_count":   rdv2_count,
        "signed":       signed,
        "avg_payback":  avg_payback,
        "due_today":    due_today,
    }


def pipeline_by_stage():
    """Return dict {stage_key: [prospects]} for kanban."""
    rows = query("SELECT * FROM prospects ORDER BY interet DESC NULLS LAST, updated_at DESC")
    out = {}
    for r in rows:
        out.setdefault(r["stage"], []).append(r)
    return out
