"""crm.app — Flask app + routes."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_login import LoginManager, current_user

# Charge .env AVANT d'importer modules qui en dépendent
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import init_db
from . import models as M
from . import auth as A
from .auth_routes import auth_bp
from .config import (
    STAGES, STAGE_KEYS, STAGE_LABELS, STAGE_COLORS,
    CATEGORIES, ACTIVITY_TYPES, TEMPLATES, STATIC,
)

app = Flask(__name__,
            template_folder=str(TEMPLATES),
            static_folder=str(STATIC))
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-key-change-me")
app.config["SESSION_COOKIE_SECURE"] = False  # True en prod HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_DURATION"] = 60 * 60 * 24 * 30   # 30 jours

# ── Flask-Login setup ────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Tu dois te connecter pour accéder à cette page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def _load_user(user_id):
    return A.get_user_by_id(user_id)


# ── Blueprints ───────────────────────────────────────────────
app.register_blueprint(auth_bp)


# Limite upload total (pièces jointes) — Resend autorise jusqu'à ~40 Mo total
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 Mo


# ── Global auth guard : tout exige login sauf /auth/* et /static/*
PUBLIC_ENDPOINTS = {"auth", "static", "public_unsubscribe"}


@app.before_request
def _require_login_everywhere():
    endpoint = request.endpoint or ""
    # Endpoints exempts (blueprint auth.*, static, unsubscribe public)
    if endpoint == "static" or endpoint.startswith("auth.") or endpoint == "public_unsubscribe":
        return None
    if current_user.is_authenticated:
        return None
    # AJAX/API → 401 JSON pour que le front gère proprement
    if request.path.startswith("/api/"):
        return jsonify({"error": "auth_required"}), 401
    return redirect(url_for("auth.login", next=request.full_path if request.path != "/" else None))


app.jinja_env.globals.update(
    STAGES=STAGES,
    STAGE_KEYS=STAGE_KEYS,
    STAGE_LABELS=STAGE_LABELS,
    STAGE_COLORS=STAGE_COLORS,
    CATEGORIES=CATEGORIES,
    ACTIVITY_TYPES=ACTIVITY_TYPES,
)


# ── Filters ────────────────────────────────────────────────────
def _parse_dt(value):
    """Parse en datetime aware (UTC si naive)."""
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


@app.template_filter("dt")
def dt_filter(value, fmt="%d/%m/%Y %H:%M"):
    dt = _parse_dt(value)
    if not dt:
        return value if isinstance(value, str) else ""
    return dt.strftime(fmt)


@app.template_filter("d")
def d_filter(value):
    return dt_filter(value, "%d/%m/%Y")


@app.template_filter("relative")
def relative_filter(value):
    dt = _parse_dt(value)
    if not dt:
        return value if isinstance(value, str) else ""
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.total_seconds() < 0:
        # date future : affiche absolu
        return dt.strftime("%d/%m/%Y %H:%M")
    if delta.days > 30:
        return dt.strftime("%d/%m/%Y")
    if delta.days >= 1:
        return f"il y a {delta.days}j"
    hours = int(delta.total_seconds() // 3600)
    if hours >= 1:
        return f"il y a {hours}h"
    minutes = max(1, int(delta.total_seconds() // 60))
    return f"il y a {minutes}min"


# ── Routes : Dashboard ────────────────────────────────────────
@app.route("/")
def dashboard():
    s = M.stats_overview()
    recent_activities = M.list_activities(limit=20)
    due = M.list_due_activities(limit=10)
    return render_template("dashboard.html",
                           stats=s,
                           recent_activities=recent_activities,
                           due_activities=due)


# ── Routes : Prospects ────────────────────────────────────────
@app.route("/prospects")
def prospects_list():
    cat = request.args.get("cat") or None
    stage = request.args.get("stage") or None
    search = request.args.get("q") or None
    ville = request.args.get("ville") or None
    rows = M.list_prospects(category=cat, stage=stage, search=search, ville=ville)
    # Extract distinct cities for filter
    villes = sorted({r["ville"] for r in M.list_prospects() if r.get("ville")}, key=str.lower)
    return render_template("prospects.html",
                           prospects=rows,
                           villes=villes,
                           filters={"cat": cat, "stage": stage, "q": search, "ville": ville})


@app.route("/prospects/<int:pid>")
def prospect_detail(pid):
    p = M.get_prospect(pid)
    if not p:
        abort(404)
    audit = M.latest_audit(pid)
    calls = M.list_calls(pid)
    activities = M.list_activities(pid)
    emails = M.list_emails(pid)
    return render_template("prospect_detail.html",
                           prospect=p, audit=audit,
                           calls=calls, activities=activities, emails=emails)


@app.route("/prospects/<int:pid>/update", methods=["POST"])
def prospect_update(pid):
    fields = {}
    for key in ("titre", "entreprise", "ville", "email",
                "phone_mobile", "phone_office", "phone_other",
                "linkedin_url", "site_url", "stage", "interet",
                "notes", "next_action"):
        v = request.form.get(key)
        if v is not None and v != "":
            if key == "interet":
                try:
                    v = int(v)
                except ValueError:
                    continue
            fields[key] = v
    if "stage" in fields:
        prev = M.get_prospect(pid)
        if prev["stage"] != fields["stage"]:
            M.create_activity(pid, "stage_change",
                              f"{STAGE_LABELS.get(prev['stage'], prev['stage'])} → {STAGE_LABELS.get(fields['stage'], fields['stage'])}",
                              user_id=current_user.id)
    M.update_prospect(pid, fields)
    return redirect(url_for("prospect_detail", pid=pid))


@app.route("/prospects/<int:pid>/note", methods=["POST"])
def prospect_add_note(pid):
    body = request.form.get("body", "").strip()
    if body:
        M.create_activity(pid, "note", "Note", body, user_id=current_user.id)
    return redirect(url_for("prospect_detail", pid=pid))


# ── Routes : Briefing live ────────────────────────────────────
@app.route("/prospects/<int:pid>/call/start", methods=["POST"])
def call_start(pid):
    p = M.get_prospect(pid)
    if not p:
        abort(404)
    call_number = 2 if p["stage"] in ("rdv_2_cale", "rdv_2_fait", "devis_envoye") else 1
    cid = M.create_call(pid, call_number=call_number, user_id=current_user.id)
    M.create_activity(pid, "call", f"Call {call_number} démarré", user_id=current_user.id)
    return redirect(url_for("call_briefing", pid=pid, cid=cid))


@app.route("/prospects/<int:pid>/call/<int:cid>")
def call_briefing(pid, cid):
    p = M.get_prospect(pid)
    call = M.get_call(cid)
    if not p or not call or call["prospect_id"] != pid:
        abort(404)
    audit = M.latest_audit(pid)
    from . import briefing_data as BD
    hook = BD.build_hook(p, audit)
    payload = BD.briefing_payload(p, audit)
    saved_state = {}
    if call.get("state"):
        try:
            saved_state = json.loads(call["state"])
        except Exception:
            saved_state = {}
    return render_template("briefing.html",
                           prospect=p, call=call, audit=audit,
                           hook_scenario=hook["scenario"],
                           hook_text=hook["hook_text"],
                           briefing_data=payload,
                           saved_state=saved_state)


@app.route("/api/calls/<int:cid>/save", methods=["POST"])
def api_call_save(cid):
    """AJAX: save call state mid-flight (autosave)."""
    call = M.get_call(cid)
    if not call:
        return jsonify({"error": "not found"}), 404
    state = request.get_json(silent=True) or {}
    M.update_call(cid, state=json.dumps(state, ensure_ascii=False))
    return jsonify({"ok": True})


@app.route("/api/calls/<int:cid>/complete", methods=["POST"])
def api_call_complete(cid):
    """AJAX: complete call → save full state + update prospect stage."""
    call = M.get_call(cid)
    if not call:
        return jsonify({"error": "not found"}), 404
    payload = request.get_json(silent=True) or {}
    state = payload.get("state", {})

    # Extract key fields from state
    statut = state.get("out_statut", "") or state.get("call2_statut", "")
    summary = state.get("out_summary", "") or state.get("call2_summary", "")
    next_action = state.get("out_next", "") or state.get("call2_next", "")
    rdv2_date = state.get("out_rdv2_date", "") or state.get("call2_signature_date", "")
    rdv2_heure = state.get("out_rdv2_heure", "")
    interet = state.get("out_interet")
    if interet:
        try: interet = int(interet)
        except: interet = None

    def _f(key):
        v = state.get(key)
        try: return float(v) if v not in (None, "") else None
        except: return None

    M.complete_call(
        cid, state=state, summary=summary, statut=statut,
        next_action=next_action,
        rdv2_date=rdv2_date, rdv2_heure=rdv2_heure, interet=interet,
        roi_valeur_client=_f("roi_valeur_client"),
        roi_leads=_f("roi_leads"),
        roi_conversion=_f("roi_conversion"),
        roi_devis=_f("roi_devis"),
        visuels_promis=state.get("out_visuels_promis"),
        budget_recu=state.get("out_budget_recu"),
    )

    # Update prospect stage based on outcome
    pid = call["prospect_id"]
    new_stage = None
    if statut == "RDV 2 calé":
        new_stage = "rdv_2_cale"
    elif statut == "Signé — acompte versé" or statut == "Signé — en attente acompte":
        new_stage = "signe"
    elif statut == "À relancer (envoyer mail récap)":
        new_stage = "en_relance"
    elif statut in ("Pas intéressé", "Refus poli"):
        new_stage = "perdu"
    elif statut == "Pas le bon moment":
        new_stage = "dormant"
    elif statut == "Répondeur / pas joignable":
        new_stage = "a_contacter"

    fields = {}
    if new_stage:
        prev = M.get_prospect(pid)
        if prev["stage"] != new_stage:
            fields["stage"] = new_stage
    fields["last_contacted_at"] = datetime.utcnow().isoformat()
    if interet:
        fields["interet"] = interet
    if next_action:
        fields["next_action"] = next_action
    if rdv2_date:
        fields["next_action_due"] = rdv2_date
    M.update_prospect(pid, fields)

    if new_stage:
        M.create_activity(
            pid, "stage_change",
            f"Stage : {STAGE_LABELS.get(prev['stage'], prev['stage'])} → {STAGE_LABELS.get(new_stage, new_stage)}",
            f"Suite à call #{call['call_number']} — statut : {statut}",
            user_id=current_user.id,
        )

    M.create_activity(pid, "call",
                      f"Call {call['call_number']} terminé — {statut or 'sans statut'}",
                      summary,
                      user_id=current_user.id)

    # Auto-create next action activity if RDV 2 calé
    if rdv2_date and new_stage == "rdv_2_cale":
        try:
            due = datetime.fromisoformat(f"{rdv2_date}T{rdv2_heure or '10:00'}:00")
            M.create_activity(pid, "meeting", f"RDV 2 — {p_name(pid)}",
                              f"Visio Calendly à {rdv2_heure or '10:00'}",
                              due_at=due.isoformat(),
                              user_id=current_user.id)
        except Exception:
            pass

    return jsonify({"ok": True, "redirect": url_for("prospect_detail", pid=pid)})


def p_name(pid):
    p = M.get_prospect(pid)
    return p["nom_complet"] if p else "?"


# ── Routes : Audit (live fetch) ───────────────────────────────
@app.route("/api/prospects/<int:pid>/audit", methods=["POST"])
def api_audit(pid):
    """Lance un audit live du site (HTTPS, headers, technos)."""
    p = M.get_prospect(pid)
    if not p:
        return jsonify({"error": "not found"}), 404
    if not p.get("site_url"):
        return jsonify({"error": "no site"}), 400
    # Importer la fonction depuis cold_call (même logique d'audit)
    import sys
    scripts_path = Path(__file__).resolve().parent.parent / "linkedin-scraper" / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    from cold_call import audit_site
    audit = audit_site(p["site_url"])
    if audit.get("ok"):
        M.save_audit(pid, audit, user_id=current_user.id)
        M.create_activity(pid, "audit", f"Audit site — {audit.get('security_grade', '?')}",
                          f"Technos: {', '.join(audit.get('technos', []))}",
                          user_id=current_user.id)
    return jsonify(audit)


# ── Routes : Emails (manuels) ─────────────────────────────────


def _make_unsubscribe_url(prospect_email: str, prospect_id: int) -> str:
    """Génère un lien de désinscription signé."""
    from itsdangerous import URLSafeTimedSerializer
    secret = os.getenv("FLASK_SECRET_KEY")
    s = URLSafeTimedSerializer(secret)
    token = s.dumps({"email": prospect_email, "pid": prospect_id}, salt="unsub")
    base = os.getenv("APP_BASE_URL", request.host_url.rstrip("/"))
    return f"{base}/unsubscribe/{token}"


@app.route("/api/prospects/<int:pid>/email/send", methods=["POST"])
def api_send_email(pid):
    """Envoi d'email manuel depuis fiche prospect.
    Accepte multipart/form-data : to, subject, body_html (et fichiers via 'attachments')."""
    import logging
    from . import email_sender as ES

    log = logging.getLogger(__name__)
    p = M.get_prospect(pid)
    if not p:
        return jsonify({"error": "not_found"}), 404

    to_email = (request.form.get("to") or p.get("email") or "").strip()
    subject  = (request.form.get("subject") or "").strip()
    body_html = (request.form.get("body_html") or "").strip()

    if not to_email or "@" not in to_email:
        return jsonify({"error": "to_email_invalid"}), 400
    if not subject:
        return jsonify({"error": "subject_required"}), 400
    if not body_html:
        return jsonify({"error": "body_required"}), 400

    # RGPD : block if unsubscribed
    if M.is_unsubscribed(to_email):
        return jsonify({
            "error": "unsubscribed",
            "message": f"{to_email} s'est désabonné. Envoi bloqué pour respect RGPD."
        }), 403

    # From logic : user.email @mad-makers.fr → as user ; else contact@... + reply-to user
    from_email, from_name, reply_to = ES.resolve_from_email(
        current_user.email, current_user.full_name
    )

    # Attachments (multipart files)
    attachments = []
    attachments_info = []
    for f in request.files.getlist("attachments"):
        if not f or not f.filename:
            continue
        content = f.read()
        attachments.append({
            "filename": f.filename,
            "content": content,
            "content_type": f.content_type or "application/octet-stream",
        })
        attachments_info.append({"filename": f.filename, "size_kb": round(len(content) / 1024, 1)})

    unsub_url = _make_unsubscribe_url(to_email, pid)

    try:
        resp = ES.send_compose_email(
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            attachments=attachments or None,
            unsubscribe_url=unsub_url,
        )
        msg_id = resp.get("id") if isinstance(resp, dict) else None

        # Log en DB
        M.log_email_sent(
            prospect_id=pid, user_id=current_user.id,
            from_email=from_email, from_name=from_name, to_email=to_email,
            reply_to=reply_to, subject=subject, body=body_html, body_html=body_html,
            resend_message_id=msg_id, attachments_info=attachments_info, status="sent",
        )

        # Activity timeline
        body_log = f"À : {to_email}"
        if attachments_info:
            body_log += f"\nPJ : {', '.join(a['filename'] for a in attachments_info)}"
        M.create_activity(
            pid, "email", f"Email envoyé — {subject[:60]}",
            body_log, user_id=current_user.id,
        )

        # Bump last_contacted_at
        M.update_prospect(pid, {"last_contacted_at": datetime.utcnow().isoformat()})

        return jsonify({"ok": True, "message_id": msg_id})

    except Exception as e:
        log.exception("send email failed")
        M.log_email_sent(
            prospect_id=pid, user_id=current_user.id,
            from_email=from_email, from_name=from_name, to_email=to_email,
            reply_to=reply_to, subject=subject, body=body_html, body_html=body_html,
            attachments_info=attachments_info, status="failed", error=str(e),
        )
        return jsonify({"error": "send_failed", "message": str(e)}), 500


# ── Routes : IA Email Generator (Claude) ──────────────────────


@app.route("/api/ai/draft-email", methods=["POST"])
def api_ai_draft_email():
    """Génère un draft d'email via Claude. Body JSON :
    { prospect_id, prompt, template_id (opt), use_audit (default true) }"""
    from . import ai as AI

    payload = request.get_json(silent=True) or {}
    pid = payload.get("prospect_id")
    user_prompt = (payload.get("prompt") or "").strip()
    tpl_id = payload.get("template_id")
    use_audit = payload.get("use_audit", True)

    if not pid:
        return jsonify({"error": "prospect_id_required"}), 400
    if not user_prompt:
        return jsonify({"error": "prompt_required",
                        "message": "Décris ce que tu veux dans l'email (ton, angle, action attendue)."}), 400

    prospect = M.get_prospect(pid)
    if not prospect:
        return jsonify({"error": "prospect_not_found"}), 404

    audit = None
    if use_audit:
        a = M.latest_audit(pid)
        if a:
            audit = {
                "ok": True,
                "security_grade": a.get("security_grade"),
                "technos": a.get("technos"),
                "veillot_tags": a.get("veillot_tags"),
                "copyright_year": a.get("copyright_year"),
                "https": a.get("https"),
            }

    base_template = None
    if tpl_id:
        t = M.get_template(tpl_id)
        if t:
            base_template = {"subject": t["subject"], "body_html": t["body_html"]}

    user_dict = {"email": current_user.email, "full_name": current_user.full_name}

    try:
        result = AI.draft_email(prospect, user_dict, user_prompt,
                                audit=audit, base_template=base_template)

        # Render variables CRM (au cas où Claude a utilisé {{xxx}})
        rendered = M.render_template_for_prospect(result, prospect, user_dict)

        return jsonify({"ok": True,
                        "subject": rendered["subject"],
                        "body_html": rendered["body_html"]})
    except Exception as e:
        import logging
        logging.exception("AI draft failed")
        return jsonify({"error": "ai_failed", "message": str(e)}), 500


# ── Routes : Email Templates (bibliothèque) ───────────────────


@app.route("/templates")
def templates_list():
    seg = request.args.get("segment") or None
    step = request.args.get("step") or None
    tpls = M.list_templates(segment=seg, step=step)
    return render_template("templates_list.html",
                           templates=tpls,
                           filters={"segment": seg, "step": step},
                           SEGMENT_LABELS=M.SEGMENT_LABELS,
                           STEP_LABELS=M.STEP_LABELS,
                           CATEGORY_LABELS=M.CATEGORY_LABELS)


@app.route("/templates/new", methods=["GET", "POST"])
def templates_new():
    if request.method == "POST":
        return _save_template(None)
    return render_template("template_form.html",
                           tpl=None,
                           SEGMENT_LABELS=M.SEGMENT_LABELS,
                           STEP_LABELS=M.STEP_LABELS,
                           CATEGORY_LABELS=M.CATEGORY_LABELS,
                           TEMPLATE_VARIABLES=M.TEMPLATE_VARIABLES)


@app.route("/templates/<int:tpl_id>", methods=["GET", "POST"])
def templates_edit(tpl_id):
    tpl = M.get_template(tpl_id)
    if not tpl:
        abort(404)
    if request.method == "POST":
        return _save_template(tpl_id)
    return render_template("template_form.html",
                           tpl=tpl,
                           SEGMENT_LABELS=M.SEGMENT_LABELS,
                           STEP_LABELS=M.STEP_LABELS,
                           CATEGORY_LABELS=M.CATEGORY_LABELS,
                           TEMPLATE_VARIABLES=M.TEMPLATE_VARIABLES)


def _save_template(tpl_id):
    name = (request.form.get("name") or "").strip()
    subject = (request.form.get("subject") or "").strip()
    body_html = (request.form.get("body_html") or "").strip()
    description = (request.form.get("description") or "").strip()
    category = request.form.get("category") or None
    segment = request.form.get("segment") or None
    step = request.form.get("step") or None

    if not name or not subject or not body_html:
        from flask import flash as _flash
        _flash("Nom, objet et corps sont requis.", "error")
        return redirect(url_for("templates_new") if not tpl_id else url_for("templates_edit", tpl_id=tpl_id))

    if tpl_id:
        M.update_template(tpl_id, name=name, subject=subject, body_html=body_html,
                          description=description, category=category,
                          segment=segment, step=step)
    else:
        tpl_id = M.create_template(
            name=name, subject=subject, body_html=body_html,
            description=description, category=category,
            segment=segment, step=step, user_id=current_user.id,
        )
    return redirect(url_for("templates_list"))


@app.route("/api/templates", methods=["GET"])
def api_templates_list():
    seg = request.args.get("segment") or None
    step = request.args.get("step") or None
    tpls = M.list_templates(segment=seg, step=step)
    return jsonify([{
        "id": t["id"], "name": t["name"], "description": t.get("description"),
        "category": t.get("category"), "segment": t.get("segment"), "step": t.get("step"),
        "subject": t["subject"],
    } for t in tpls])


@app.route("/api/templates/<int:tpl_id>/render", methods=["GET"])
def api_template_render(tpl_id):
    """Rend un template avec les variables remplies depuis un prospect."""
    tpl = M.get_template(tpl_id)
    if not tpl:
        return jsonify({"error": "not_found"}), 404
    pid = request.args.get("prospect_id", type=int)
    prospect = M.get_prospect(pid) if pid else {}
    user = {
        "email": current_user.email,
        "full_name": current_user.full_name,
    }
    out = M.render_template_for_prospect(tpl, prospect or {}, user)
    return jsonify({"subject": out["subject"], "body_html": out["body_html"],
                    "name": tpl["name"]})


@app.route("/api/templates/<int:tpl_id>/archive", methods=["POST"])
def api_template_archive(tpl_id):
    M.archive_template(tpl_id)
    return jsonify({"ok": True})


@app.route("/api/templates/<int:tpl_id>/delete", methods=["POST"])
def api_template_delete(tpl_id):
    M.delete_template(tpl_id)
    return jsonify({"ok": True})


# ── Routes : Unsubscribe (public, no auth) ────────────────────


@app.route("/unsubscribe/<token>", methods=["GET", "POST"])
def public_unsubscribe(token):
    """Page publique de désabonnement (lien dans chaque email)."""
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

    secret = os.getenv("FLASK_SECRET_KEY")
    s = URLSafeTimedSerializer(secret)
    try:
        data = s.loads(token, salt="unsub")
    except SignatureExpired:
        return render_template("unsubscribe.html", state="expired"), 410
    except BadSignature:
        return render_template("unsubscribe.html", state="invalid"), 400

    email = data.get("email", "").strip().lower()
    pid = data.get("pid")

    if request.method == "POST":
        reason = (request.form.get("reason") or "").strip()
        ua = request.headers.get("User-Agent", "")[:200]
        M.add_unsubscribe(email, prospect_id=pid, reason=reason, user_agent=ua)
        # Log activity sur le prospect si on a un pid
        if pid:
            try:
                M.create_activity(pid, "note", "Désabonnement RGPD",
                                  f"L'email {email} s'est désabonné. Raison : {reason or '(non précisée)'}")
            except Exception:
                pass
        return render_template("unsubscribe.html", state="confirmed", email=email)

    already = M.is_unsubscribed(email)
    return render_template("unsubscribe.html",
                           state="already" if already else "confirm",
                           email=email, token=token)


# Exempt public_unsubscribe du global auth guard (déclaré APRÈS before_request,
# on doit donc tester explicitement)
# → géré dans _require_login_everywhere ci-dessous (endpoint 'public_unsubscribe')


# ── Routes : Pipeline kanban ──────────────────────────────────
@app.route("/pipeline")
def pipeline():
    by_stage = M.pipeline_by_stage()
    return render_template("pipeline.html", by_stage=by_stage)


@app.route("/api/prospects/<int:pid>/stage", methods=["POST"])
def api_set_stage(pid):
    new_stage = (request.get_json(silent=True) or {}).get("stage")
    if new_stage not in STAGE_KEYS:
        return jsonify({"error": "invalid stage"}), 400
    prev = M.get_prospect(pid)
    if not prev:
        return jsonify({"error": "not found"}), 404
    if prev["stage"] != new_stage:
        M.update_prospect(pid, {"stage": new_stage})
        M.create_activity(pid, "stage_change",
                          f"{STAGE_LABELS.get(prev['stage'])} → {STAGE_LABELS.get(new_stage)}",
                          "Drag & drop kanban",
                          user_id=current_user.id)
    return jsonify({"ok": True})


# ── Routes : Activities ───────────────────────────────────────
@app.route("/activities")
def activities_list():
    due = M.list_due_activities(limit=100)
    recent = M.list_activities(limit=100)
    return render_template("activities.html", due=due, recent=recent)


@app.route("/api/activities/<int:aid>/complete", methods=["POST"])
def api_complete_activity(aid):
    M.complete_activity(aid)
    return jsonify({"ok": True})


# ── Routes : Imports ──────────────────────────────────────────
@app.route("/imports")
def imports_view():
    return render_template("imports.html")


# ── Bootstrap ─────────────────────────────────────────────────
def create_app():
    init_db()
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000, debug=True)
