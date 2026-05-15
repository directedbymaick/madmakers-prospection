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


# ── Global auth guard : tout exige login sauf /auth/* et /static/*
@app.before_request
def _require_login_everywhere():
    # Endpoints exempts (préfixes "auth." du blueprint + "static")
    endpoint = request.endpoint or ""
    if endpoint.startswith("auth.") or endpoint == "static":
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
