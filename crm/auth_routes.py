"""crm.auth_routes — Flask Blueprint pour signup / login / verify / reset."""
import os
import logging
from urllib.parse import urlparse, urljoin

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app, abort
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)

from . import auth as A
from . import email_sender as ES

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─── Helpers ──────────────────────────────────────────────────


def _safe_next(target):
    """Empêche les open-redirects sur ?next=."""
    if not target:
        return None
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    if test.scheme in ("http", "https") and ref.netloc == test.netloc:
        return target
    return None


def _validate_password(pw: str) -> str | None:
    if not pw or len(pw) < 8:
        return "Le mot de passe doit faire au moins 8 caractères."
    if not any(c.isupper() for c in pw):
        return "Au moins 1 majuscule requise."
    if not any(c.isdigit() for c in pw):
        return "Au moins 1 chiffre requis."
    return None


def _base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


# ─── Signup ───────────────────────────────────────────────────


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        full_name = (request.form.get("full_name") or "").strip()

        # Validations
        if not email or "@" not in email:
            flash("Email invalide.", "error")
            return render_template("auth/signup.html", form={"email": email, "full_name": full_name})

        if not A.is_email_allowed(email):
            flash("Cet email n'est pas autorisé. Demande à Maïck d'ajouter ton adresse à la whitelist.", "error")
            return render_template("auth/signup.html", form={"email": email, "full_name": full_name})

        if A.get_user_by_email(email):
            flash("Un compte existe déjà avec cet email. Connecte-toi ou réinitialise ton mot de passe.", "error")
            return redirect(url_for("auth.login"))

        if password != password2:
            flash("Les deux mots de passe ne correspondent pas.", "error")
            return render_template("auth/signup.html", form={"email": email, "full_name": full_name})

        err = _validate_password(password)
        if err:
            flash(err, "error")
            return render_template("auth/signup.html", form={"email": email, "full_name": full_name})

        # Création + envoi email
        try:
            uid = A.create_user(email, password, full_name)
        except Exception as e:
            log.exception("create_user failed")
            flash(f"Erreur lors de la création du compte : {e}", "error")
            return render_template("auth/signup.html", form={"email": email, "full_name": full_name})

        token = A.make_verify_token(uid)
        verify_url = f"{_base_url()}{url_for('auth.verify_email', token=token)}"

        try:
            ES.send_verification_email(email, verify_url, full_name)
            A.touch_verification_sent(uid)
        except Exception as e:
            log.exception("send_verification_email failed")
            flash(f"Compte créé mais erreur d'envoi d'email : {e}. Demande au support de te renvoyer le lien.", "error")
            return redirect(url_for("auth.login"))

        return render_template("auth/verify_sent.html", email=email)

    return render_template("auth/signup.html", form={})


# ─── Email verification ───────────────────────────────────────


@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        data = A.read_verify_token(token)
    except A.SignatureExpired:
        flash("Ce lien de vérification a expiré (24h). Demande un nouveau lien.", "error")
        return redirect(url_for("auth.resend_verification"))
    except A.BadSignature:
        flash("Lien de vérification invalide.", "error")
        return redirect(url_for("auth.login"))

    uid = data.get("uid")
    user = A.get_user_by_id(uid)
    if not user:
        flash("Compte introuvable.", "error")
        return redirect(url_for("auth.login"))

    if user.email_verified:
        flash("Ton email est déjà vérifié. Connecte-toi.", "info")
        return redirect(url_for("auth.login"))

    A.mark_email_verified(uid)
    try:
        ES.send_welcome_email(user.email, user.full_name)
    except Exception:
        log.exception("send_welcome_email failed (non-blocking)")

    flash("Email vérifié. Tu peux maintenant te connecter.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = A.get_user_by_email(email)
        # Toujours afficher succès pour ne pas révéler l'existence d'un compte
        if user and not user.email_verified:
            try:
                token = A.make_verify_token(user.id)
                verify_url = f"{_base_url()}{url_for('auth.verify_email', token=token)}"
                ES.send_verification_email(email, verify_url, user.full_name)
                A.touch_verification_sent(user.id)
            except Exception:
                log.exception("resend verification failed")
        flash("Si un compte non-vérifié existe pour cet email, un nouveau lien vient d'être envoyé.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/resend_verification.html")


# ─── Login ────────────────────────────────────────────────────


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        user = A.get_user_by_email(email)
        if not user or not A.verify_password(password, user.password_hash):
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("auth/login.html", form={"email": email})

        if not user.email_verified:
            flash("Tu dois d'abord vérifier ton email. Vérifie ta boite (et tes spams).", "error")
            return render_template("auth/login.html", form={"email": email}, unverified=True)

        if not user._is_active:
            flash("Ce compte est désactivé. Contacte Maïck.", "error")
            return render_template("auth/login.html", form={"email": email})

        login_user(user, remember=remember)
        A.touch_last_login(user.id)

        target = _safe_next(request.args.get("next"))
        return redirect(target or url_for("dashboard"))

    return render_template("auth/login.html", form={})


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Tu es déconnecté.", "info")
    return redirect(url_for("auth.login"))


# ─── Password reset ───────────────────────────────────────────


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = A.get_user_by_email(email)
        if user:
            try:
                token = A.make_reset_token(user.id)
                reset_url = f"{_base_url()}{url_for('auth.reset', token=token)}"
                ES.send_reset_password_email(email, reset_url, user.full_name)
            except Exception:
                log.exception("send_reset failed")
        # Toujours succès, ne pas révéler l'existence du compte
        flash("Si un compte existe pour cet email, un lien de réinitialisation vient d'être envoyé.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot.html")


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    try:
        data = A.read_reset_token(token)
    except A.SignatureExpired:
        flash("Ce lien de réinitialisation a expiré (1h). Demande un nouveau lien.", "error")
        return redirect(url_for("auth.forgot"))
    except A.BadSignature:
        flash("Lien invalide.", "error")
        return redirect(url_for("auth.forgot"))

    uid = data.get("uid")
    user = A.get_user_by_id(uid)
    if not user:
        flash("Compte introuvable.", "error")
        return redirect(url_for("auth.forgot"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if password != password2:
            flash("Les deux mots de passe ne correspondent pas.", "error")
            return render_template("auth/reset.html", token=token)

        err = _validate_password(password)
        if err:
            flash(err, "error")
            return render_template("auth/reset.html", token=token)

        A.update_password(uid, password)
        flash("Mot de passe mis à jour. Connecte-toi avec le nouveau.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset.html", token=token)


# ─── Profile (basique) ────────────────────────────────────────


@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")
