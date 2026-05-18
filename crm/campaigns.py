"""crm.campaigns — modèles + logique métier pour les campagnes d'emails.

Workflow campagne :
1. User crée une campagne (name, description, signataire)
2. User assigne N prospects (depuis filtres avancés ou sélection)
3. User définit N steps (template + delay_days)
4. User clique "Lancer" → status=active + started_at=NOW
5. Le cron worker (process_due_emails) :
   - Pour chaque (campaign active, target active, step manquant) :
     - Si scheduled_at <= NOW() OU pas encore d'email pour cette step :
       - Crée un email avec scheduled_at = started_at + delay_days
       - Si scheduled_at <= NOW(), l'envoie immédiatement
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .db import query, query_one, execute

log = logging.getLogger(__name__)


# ── Statuts ───────────────────────────────────────────────────

CAMPAIGN_STATUSES = {
    "draft":     ("Brouillon",    "#6B7280"),
    "active":    ("Active",       "#22C55E"),
    "paused":    ("En pause",     "#F59E0B"),
    "completed": ("Terminée",     "#0EA5E9"),
}

TARGET_STATUSES = {
    "active":    ("Active",       "#22C55E"),
    "paused":    ("Pause",        "#F59E0B"),
    "completed": ("Terminée",     "#0EA5E9"),
    "stopped":   ("Stoppée",      "#6B7280"),
    "failed":    ("Échec",        "#EF4444"),
}


# ── CRUD Campagnes ────────────────────────────────────────────


def list_campaigns(status=None, limit=None):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM campaign_targets t WHERE t.campaign_id = c.id) AS targets_count,
               (SELECT COUNT(*) FROM campaign_steps s WHERE s.campaign_id = c.id) AS steps_count,
               (SELECT COUNT(*) FROM emails e WHERE e.campaign_id = c.id AND e.status = 'sent') AS sent_count
        FROM campaigns c
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND c.status = ?"; params.append(status)
    sql += " ORDER BY c.created_at DESC"
    if limit:
        sql += " LIMIT ?"; params.append(limit)
    return query(sql, params)


def get_campaign(cid):
    return query_one("SELECT * FROM campaigns WHERE id = ?", (cid,))


def get_campaign_detail(cid):
    """Retourne campagne + steps + stats."""
    c = get_campaign(cid)
    if not c:
        return None
    c["steps"] = list_steps(cid)
    c["targets_count"] = query_one(
        "SELECT COUNT(*) AS n FROM campaign_targets WHERE campaign_id = ?", (cid,))["n"]
    # Stats par statut target
    rows = query("""
        SELECT status, COUNT(*) AS n FROM campaign_targets
        WHERE campaign_id = ? GROUP BY status
    """, (cid,))
    c["targets_by_status"] = {r["status"]: r["n"] for r in rows}
    # Stats emails
    rows = query("""
        SELECT status, COUNT(*) AS n FROM emails
        WHERE campaign_id = ? GROUP BY status
    """, (cid,))
    c["emails_by_status"] = {r["status"]: r["n"] for r in rows}
    return c


def create_campaign(*, name, description=None, from_user_id=None, user_id=None,
                    daily_send_limit=None):
    return execute(
        """INSERT INTO campaigns
           (name, description, from_user_id, created_by_user_id, daily_send_limit, status)
           VALUES (?, ?, ?, ?, ?, 'draft')""",
        (name, description, from_user_id, user_id, daily_send_limit),
    )


def update_campaign(cid, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    cols = list(fields.keys())
    sql = f"UPDATE campaigns SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?"
    execute(sql, list(fields.values()) + [cid])


def delete_campaign(cid):
    execute("DELETE FROM campaigns WHERE id = ?", (cid,))


def launch_campaign(cid):
    """Passe en status=active + started_at=NOW.
    Le cron prendra le relais pour programmer/envoyer les emails."""
    now = datetime.utcnow().isoformat()
    update_campaign(cid, status="active", started_at=now)


def pause_campaign(cid):
    update_campaign(cid, status="paused")


def resume_campaign(cid):
    update_campaign(cid, status="active")


# ── Steps ─────────────────────────────────────────────────────


def list_steps(campaign_id):
    return query(
        """SELECT s.*, t.name AS template_name, t.subject AS template_subject
           FROM campaign_steps s
           LEFT JOIN email_templates t ON t.id = s.template_id
           WHERE s.campaign_id = ?
           ORDER BY s.step_number""",
        (campaign_id,),
    )


def add_step(campaign_id, *, step_number, delay_days=0, delay_hours=0,
             template_id=None, custom_subject=None, custom_body=None):
    return execute(
        """INSERT INTO campaign_steps
           (campaign_id, step_number, delay_days, delay_hours, template_id,
            custom_subject, custom_body)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (campaign_id, step_number, delay_days, delay_hours,
         template_id, custom_subject, custom_body),
    )


def delete_step(step_id):
    execute("DELETE FROM campaign_steps WHERE id = ?", (step_id,))


def update_step(step_id, **fields):
    if not fields:
        return
    cols = list(fields.keys())
    sql = f"UPDATE campaign_steps SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?"
    execute(sql, list(fields.values()) + [step_id])


# ── Targets (prospects assignés) ──────────────────────────────


def list_targets(campaign_id, status=None, limit=None):
    sql = """
        SELECT t.*, p.nom_complet, p.entreprise, p.titre, p.email, p.ville, p.categorie
        FROM campaign_targets t
        JOIN prospects p ON p.id = t.prospect_id
        WHERE t.campaign_id = ?
    """
    params = [campaign_id]
    if status:
        sql += " AND t.status = ?"; params.append(status)
    sql += " ORDER BY t.started_at DESC"
    if limit:
        sql += " LIMIT ?"; params.append(limit)
    return query(sql, params)


def assign_prospects(campaign_id, prospect_ids):
    """Assigne une liste de prospects à la campagne. Skip les doublons.
    Retourne le nombre effectivement ajoutés."""
    added = 0
    for pid in prospect_ids:
        existing = query_one(
            "SELECT id FROM campaign_targets WHERE campaign_id = ? AND prospect_id = ?",
            (campaign_id, pid),
        )
        if existing:
            continue
        execute(
            """INSERT INTO campaign_targets (campaign_id, prospect_id, status)
               VALUES (?, ?, 'active')""",
            (campaign_id, pid),
        )
        added += 1
    return added


def stop_target(target_id, reason="manual"):
    now = datetime.utcnow().isoformat()
    execute(
        """UPDATE campaign_targets
           SET status = 'stopped', stop_reason = ?, completed_at = ?
           WHERE id = ?""",
        (reason, now, target_id),
    )


def mark_target_completed(target_id):
    now = datetime.utcnow().isoformat()
    execute(
        """UPDATE campaign_targets
           SET status = 'completed', completed_at = ?
           WHERE id = ?""",
        (now, target_id),
    )


# ── Worker : programme les prochains emails dûs ──────────────


def _shift_to_business_day(dt: datetime) -> datetime:
    """Si dt tombe samedi/dimanche, pousse au lundi suivant à la même heure."""
    while dt.weekday() >= 5:  # 5 = samedi, 6 = dimanche
        dt = dt + timedelta(days=1)
    return dt


def _add_business_days(dt: datetime, n_days: int) -> datetime:
    """Ajoute n jours OUVRÉS (lun-ven) à dt. n=0 retourne dt (shifté si week-end)."""
    dt = _shift_to_business_day(dt)
    remaining = n_days
    while remaining > 0:
        dt = dt + timedelta(days=1)
        if dt.weekday() < 5:
            remaining -= 1
    return dt


def schedule_pending_emails(*, dry_run: bool = False) -> dict:
    """Pour chaque campagne active, target active, step manquant :
    crée un email avec scheduled_at.

    Si campaign.daily_send_limit est défini, le step J0 (delay_days=0) est
    étalé sur plusieurs jours ouvrés à hauteur de N envois/jour. Les steps
    suivants (J+4, J+10, J+18) sont relatifs au scheduled_at du J0 du même
    prospect, pas au started_at de la campagne — comme ça toute la séquence
    suit la même cadence et les week-ends sont skippés.

    Idempotent : ne crée pas de doublon si un email existe déjà pour
    (campaign_id, prospect_id, step_id).

    Retourne {scheduled, skipped}.
    """
    scheduled = 0
    skipped = 0

    campaigns = query("SELECT * FROM campaigns WHERE status = 'active'")
    for c in campaigns:
        steps = list_steps(c["id"])
        if not steps:
            continue
        targets = list_targets(c["id"], status="active")

        started_at = c.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        # Daily limit : on calcule l'offset J0 par target dans l'ordre
        # stable de campaign_targets.id (= ordre d'ajout). targets[i] sera
        # programmé sur day = i // daily_limit (en jours ouvrés).
        daily_limit = c.get("daily_send_limit")

        for idx, t in enumerate(targets):
            # Cadence J0 pour ce target — compte en jours OUVRÉS, pas calendaires
            if daily_limit and daily_limit > 0:
                day_offset = idx // daily_limit
            else:
                day_offset = 0
            # heure jitterée stable : entre 9h et 17h UTC, pseudo-random par target
            hour_jitter = 9 + (t["prospect_id"] % 9)
            min_jitter = (t["prospect_id"] * 7) % 60

            j0_at = _add_business_days(
                started_at.replace(hour=hour_jitter, minute=min_jitter, second=0, microsecond=0),
                day_offset,
            )

            for step in steps:
                # email existe déjà pour ce (target, step) ?
                existing = query_one(
                    """SELECT id, status FROM emails
                       WHERE campaign_id = ? AND prospect_id = ? AND campaign_step_id = ?""",
                    (c["id"], t["prospect_id"], step["id"]),
                )
                if existing:
                    continue

                # Tous les steps sont relatifs au J0 de CE target (pas de la campagne)
                # → la cadence J+4 / J+10 reste cohérente même si le J0 est repoussé
                scheduled_at = _shift_to_business_day(
                    j0_at + timedelta(
                        days=step["delay_days"] or 0,
                        hours=step["delay_hours"] or 0,
                    )
                )

                if dry_run:
                    scheduled += 1
                    continue

                # Crée l'email en draft scheduled
                subject = step.get("custom_subject")
                body = step.get("custom_body")
                if not subject or not body:
                    # Charge depuis le template
                    if step.get("template_id"):
                        tpl = query_one(
                            "SELECT subject, body_html FROM email_templates WHERE id = ?",
                            (step["template_id"],),
                        )
                        if tpl:
                            subject = subject or tpl["subject"]
                            body = body or tpl["body_html"]

                if not subject or not body:
                    skipped += 1
                    continue

                execute(
                    """INSERT INTO emails
                       (prospect_id, sequence_step, subject, body_html, body,
                        status, scheduled_at, campaign_id, campaign_step_id)
                       VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)""",
                    (t["prospect_id"], f"campaign_step_{step['step_number']}",
                     subject, body, body,
                     scheduled_at.isoformat(),
                     c["id"], step["id"]),
                )
                scheduled += 1

    return {"scheduled": scheduled, "skipped": skipped}


def process_due_emails(limit: int = 50) -> dict:
    """Envoie tous les emails dont status='scheduled' AND scheduled_at <= NOW.
    Limite par batch pour éviter de saturer Resend.

    Retourne {sent, failed, blocked_rgpd}.
    """
    from . import models as M
    from . import email_sender as ES

    sent = 0
    failed = 0
    blocked_rgpd = 0
    completed_targets = 0

    rows = query(
        """SELECT e.*, p.email AS prospect_email, p.nom_complet,
                  c.from_user_id, u.email AS user_email, u.full_name AS user_full_name
           FROM emails e
           JOIN prospects p ON p.id = e.prospect_id
           LEFT JOIN campaigns c ON c.id = e.campaign_id
           LEFT JOIN users u ON u.id = c.from_user_id
           WHERE e.status = 'scheduled' AND e.scheduled_at <= NOW()
           ORDER BY e.scheduled_at ASC LIMIT ?""",
        (limit,),
    )

    for em in rows:
        to_email = em.get("to_email") or em.get("prospect_email")
        if not to_email:
            execute("UPDATE emails SET status = 'failed', error_message = 'no_recipient' WHERE id = ?",
                    (em["id"],))
            failed += 1
            continue

        # RGPD : blocked si désabonné
        if M.is_unsubscribed(to_email):
            execute(
                """UPDATE emails SET status = 'failed', error_message = 'unsubscribed'
                   WHERE id = ?""",
                (em["id"],),
            )
            # Stop le target dans la campagne
            if em.get("campaign_id"):
                execute(
                    """UPDATE campaign_targets
                       SET status = 'stopped', stop_reason = 'unsubscribed',
                           completed_at = NOW()
                       WHERE campaign_id = ? AND prospect_id = ? AND status = 'active'""",
                    (em["campaign_id"], em["prospect_id"]),
                )
            blocked_rgpd += 1
            continue

        # Compose et envoie
        user_email = em.get("user_email") or ""
        user_name = em.get("user_full_name") or ""
        from_email, from_name, reply_to = ES.resolve_from_email(user_email, user_name)

        # Render variables avec les data prospect
        prospect = M.get_prospect(em["prospect_id"])
        user_dict = {"email": user_email, "full_name": user_name}
        rendered = M.render_template_for_prospect(
            {"subject": em["subject"], "body_html": em["body_html"]},
            prospect or {}, user_dict,
        )

        unsub_url = _make_unsubscribe_url(to_email, em["prospect_id"])

        try:
            resp = ES.send_compose_email(
                from_email=from_email,
                from_name=from_name,
                reply_to=reply_to,
                to_email=to_email,
                subject=rendered["subject"],
                body_html=rendered["body_html"],
                unsubscribe_url=unsub_url,
            )
            msg_id = resp.get("id") if isinstance(resp, dict) else None
            execute(
                """UPDATE emails
                   SET status = 'sent', sent_at = NOW(),
                       resend_message_id = ?,
                       from_email = ?, from_name = ?, to_email = ?, reply_to = ?,
                       subject = ?, body_html = ?, body = ?
                   WHERE id = ?""",
                (msg_id, from_email, from_name, to_email, reply_to,
                 rendered["subject"], rendered["body_html"], rendered["body_html"],
                 em["id"]),
            )

            # Update last_step_sent du target
            if em.get("campaign_id") and em.get("campaign_step_id"):
                step_row = query_one(
                    "SELECT step_number FROM campaign_steps WHERE id = ?",
                    (em["campaign_step_id"],),
                )
                step_n = step_row["step_number"] if step_row else 0
                execute(
                    """UPDATE campaign_targets
                       SET last_step_sent = GREATEST(last_step_sent, ?)
                       WHERE campaign_id = ? AND prospect_id = ?""",
                    (step_n, em["campaign_id"], em["prospect_id"]),
                )

                # Si c'était le dernier step, mark target completed
                last_step = query_one(
                    """SELECT MAX(step_number) AS m FROM campaign_steps
                       WHERE campaign_id = ?""",
                    (em["campaign_id"],),
                )
                if last_step and step_n >= (last_step["m"] or 0):
                    execute(
                        """UPDATE campaign_targets
                           SET status = 'completed', completed_at = NOW()
                           WHERE campaign_id = ? AND prospect_id = ?""",
                        (em["campaign_id"], em["prospect_id"]),
                    )
                    completed_targets += 1

            # Activity timeline
            M.create_activity(
                em["prospect_id"], "email",
                f"Email auto envoyé — campagne #{em.get('campaign_id', '?')} step",
                f"À : {to_email} · Subject : {rendered['subject'][:80]}",
                user_id=em.get("from_user_id"),
            )

            sent += 1
        except Exception as e:
            log.exception(f"send failed for email {em['id']}")
            execute(
                "UPDATE emails SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e)[:500], em["id"]),
            )
            failed += 1

    # Toutes les campagnes dont tous les targets sont completed/stopped → completed
    rows = query("""
        SELECT c.id FROM campaigns c WHERE c.status = 'active'
        AND NOT EXISTS (
            SELECT 1 FROM campaign_targets t
            WHERE t.campaign_id = c.id AND t.status = 'active'
        )
        AND EXISTS (
            SELECT 1 FROM campaign_targets t WHERE t.campaign_id = c.id
        )
    """)
    for r in rows:
        execute(
            "UPDATE campaigns SET status = 'completed', completed_at = NOW() WHERE id = ?",
            (r["id"],),
        )

    return {"sent": sent, "failed": failed, "blocked_rgpd": blocked_rgpd,
            "completed_targets": completed_targets}


def _make_unsubscribe_url(email: str, prospect_id: int) -> str:
    import os as _os
    from itsdangerous import URLSafeTimedSerializer
    secret = _os.getenv("FLASK_SECRET_KEY")
    s = URLSafeTimedSerializer(secret)
    token = s.dumps({"email": email, "pid": prospect_id}, salt="unsub")
    base = _os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/unsubscribe/{token}"
