"""crm.email_sender — envoi d'emails via Resend (vérification, reset password)."""
import os
import logging
from typing import Optional

import resend

log = logging.getLogger(__name__)


def _init_resend():
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY non défini dans .env")
    resend.api_key = api_key


def _from_addr() -> str:
    name = os.getenv("RESEND_FROM_NAME", "Mad Makers CRM")
    email = os.getenv("RESEND_FROM_EMAIL", "noreply@mad-makers.fr")
    return f"{name} <{email}>"


def _send(to_email: str, subject: str, html: str, text: Optional[str] = None) -> dict:
    """Envoi bas-niveau via Resend. Retourne le dict de réponse."""
    _init_resend()
    params = {
        "from":    _from_addr(),
        "to":      [to_email],
        "subject": subject,
        "html":    html,
    }
    if text:
        params["text"] = text
    try:
        return resend.Emails.send(params)
    except Exception as e:
        log.error(f"Resend send failed to {to_email}: {e}")
        raise


# ─── Templates HTML inline (cohérents avec Mad Makers branding) ───


def _wrap_html(title: str, body_html: str, button_url: str = "", button_label: str = "") -> str:
    """Wrap content in Mad Makers branded HTML."""
    btn = ""
    if button_url and button_label:
        btn = f"""
        <table cellpadding="0" cellspacing="0" border="0" style="margin: 28px 0;">
            <tr><td>
                <a href="{button_url}"
                   style="display: inline-block; padding: 14px 32px;
                          background: #c8ff3d; color: #0c0d0a;
                          font-family: 'Montserrat', Arial, sans-serif;
                          font-weight: 700; font-size: 13px; letter-spacing: 0.08em;
                          text-transform: uppercase; text-decoration: none;
                          border-radius: 999px;">
                    {button_label}
                </a>
            </td></tr>
        </table>
        """
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background: #0c0d0a; font-family: 'Inter', Arial, sans-serif; color: #f1ece0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #0c0d0a;">
<tr><td align="center" style="padding: 40px 20px;">

<table cellpadding="0" cellspacing="0" border="0" width="560" style="max-width: 560px; background: #141511; border: 1px solid rgba(241,236,224,0.10); border-radius: 14px;">
<tr><td style="padding: 36px 36px 24px;">

    <h1 style="margin: 0 0 8px; font-family: 'Playfair Display', Georgia, serif; font-style: italic; font-weight: 400; font-size: 28px; letter-spacing: -0.02em; color: #f1ece0;">
        Mad Makers
    </h1>
    <p style="margin: 0; font-family: 'Roboto Mono', monospace; font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: #6b6a62;">
        CRM — Notification
    </p>

    <hr style="border: 0; border-top: 1px solid rgba(241,236,224,0.10); margin: 24px 0;">

    <div style="font-size: 15px; line-height: 1.65; color: #f1ece0;">
        {body_html}
    </div>

    {btn}

</td></tr>
</table>

<p style="margin: 24px 0 0; font-family: 'Roboto Mono', monospace; font-size: 10.5px; letter-spacing: 0.10em; text-transform: uppercase; color: #6b6a62; text-align: center;">
    Mad Makers · mad-makers.fr · contact@mad-makers.fr
</p>

</td></tr>
</table>
</body>
</html>"""


def send_verification_email(to_email: str, verify_url: str, full_name: str = "") -> dict:
    name = full_name or to_email.split("@")[0]
    body = f"""
    <p>Bonjour {name},</p>
    <p>Bienvenue dans le CRM Mad Makers. Pour activer ton compte, clique sur le bouton ci-dessous.</p>
    <p style="color: #a4a298; font-size: 13px;">Ce lien expire dans <b style="color: #c8ff3d;">24 heures</b>. Si tu n'as pas créé ce compte, ignore simplement cet email.</p>
    """
    html = _wrap_html(
        title="Active ton compte Mad Makers CRM",
        body_html=body,
        button_url=verify_url,
        button_label="Activer mon compte",
    )
    text = (
        f"Bonjour {name},\n\n"
        f"Pour activer ton compte Mad Makers CRM, ouvre ce lien :\n{verify_url}\n\n"
        f"Ce lien expire dans 24h. Si tu n'as pas créé ce compte, ignore cet email."
    )
    return _send(to_email, "Active ton compte — Mad Makers CRM", html, text)


def send_reset_password_email(to_email: str, reset_url: str, full_name: str = "") -> dict:
    name = full_name or to_email.split("@")[0]
    body = f"""
    <p>Bonjour {name},</p>
    <p>Tu as demandé à réinitialiser ton mot de passe. Clique sur le bouton ci-dessous pour en définir un nouveau.</p>
    <p style="color: #a4a298; font-size: 13px;">Ce lien expire dans <b style="color: #c8ff3d;">1 heure</b>. Si tu n'as pas fait cette demande, ignore cet email — ton mot de passe reste inchangé.</p>
    """
    html = _wrap_html(
        title="Réinitialise ton mot de passe Mad Makers CRM",
        body_html=body,
        button_url=reset_url,
        button_label="Définir un nouveau mot de passe",
    )
    text = (
        f"Bonjour {name},\n\n"
        f"Réinitialise ton mot de passe via ce lien :\n{reset_url}\n\n"
        f"Lien valide 1h. Si tu n'es pas à l'origine de la demande, ignore cet email."
    )
    return _send(to_email, "Réinitialise ton mot de passe — Mad Makers CRM", html, text)


def send_welcome_email(to_email: str, full_name: str = "") -> dict:
    """Envoyé après vérification d'email — soft welcome."""
    name = full_name or to_email.split("@")[0]
    body = f"""
    <p>Bienvenue {name},</p>
    <p>Ton compte est <b style="color: #c8ff3d;">activé</b>. Tu peux désormais te connecter au CRM Mad Makers et accéder à l'ensemble des fonctionnalités :</p>
    <ul style="margin: 16px 0; padding-left: 20px; color: #a4a298;">
        <li>500 prospects qualifiés</li>
        <li>Briefing cold call temps réel avec ROI calculator</li>
        <li>Pipeline kanban drag & drop</li>
        <li>Timeline + activités</li>
    </ul>
    """
    base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
    html = _wrap_html(
        title="Bienvenue dans le CRM Mad Makers",
        body_html=body,
        button_url=base_url,
        button_label="Accéder au CRM",
    )
    text = f"Bienvenue {name}. Ton compte est activé. CRM : {base_url}"
    return _send(to_email, "Bienvenue dans le CRM Mad Makers", html, text)
