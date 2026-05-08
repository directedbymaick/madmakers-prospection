"""crm.models — query helpers for prospects, calls, activities, audits, emails."""
import json
from datetime import datetime
from .db import query, query_one, execute, execute_many

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


def save_audit(prospect_id, audit_dict):
    raw = json.dumps(audit_dict, ensure_ascii=False)
    sql = """INSERT INTO audits (prospect_id, final_url, https, tls_version,
             security_grade, technos, veillot_tags, title, description, h1,
             copyright_year, html_size_kb, image_count, modern_image_count,
             findings, raw_data)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    return execute(sql, (
        prospect_id,
        audit_dict.get("final_url", ""),
        1 if audit_dict.get("https") else 0,
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


def create_call(prospect_id, call_number=1):
    """Start a new call session — inserts a draft row, returns id."""
    return execute(
        "INSERT INTO calls (prospect_id, call_number) VALUES (?, ?)",
        (prospect_id, call_number),
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


def list_activities(prospect_id=None, limit=50):
    if prospect_id:
        return query(
            "SELECT * FROM activities WHERE prospect_id = ? ORDER BY created_at DESC LIMIT ?",
            (prospect_id, limit),
        )
    return query(
        """SELECT a.*, p.nom_complet AS prospect_name, p.entreprise AS prospect_entreprise
           FROM activities a
           LEFT JOIN prospects p ON p.id = a.prospect_id
           ORDER BY a.created_at DESC LIMIT ?""",
        (limit,),
    )


def list_due_activities(limit=20):
    """Activities with due_at <= now and not completed."""
    return query(
        """SELECT a.*, p.nom_complet AS prospect_name, p.entreprise AS prospect_entreprise
           FROM activities a
           LEFT JOIN prospects p ON p.id = a.prospect_id
           WHERE a.due_at IS NOT NULL AND a.completed_at IS NULL
           ORDER BY a.due_at ASC LIMIT ?""",
        (limit,),
    )


def create_activity(prospect_id, type_, title, body=None, due_at=None, metadata=None):
    return execute(
        """INSERT INTO activities (prospect_id, type, title, body, due_at, metadata)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (prospect_id, type_, title, body or "", due_at,
         json.dumps(metadata, ensure_ascii=False) if metadata else None),
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
           AND completed_at >= datetime('now', '-7 days')"""
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
           AND date(due_at) <= date('now')"""
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
