-- ============================================================
-- Mad Makers CRM — schéma PostgreSQL (Supabase)
-- ============================================================

-- ── Users (auth) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT,
    role            TEXT NOT NULL DEFAULT 'user',   -- user / admin
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    verification_sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── Prospects (table maître) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS prospects (
    id                  BIGSERIAL PRIMARY KEY,
    nom_complet         TEXT NOT NULL,
    prenom              TEXT,
    nom                 TEXT,
    titre               TEXT,
    entreprise          TEXT,
    ville               TEXT,
    email               TEXT,
    phone_mobile        TEXT,
    phone_office        TEXT,
    phone_other         TEXT,
    linkedin_url        TEXT,
    entreprise_linkedin TEXT,
    site_url            TEXT,
    domaine             TEXT,
    -- Triage Mad Makers
    categorie           TEXT NOT NULL DEFAULT 'sans_site',  -- sans_site / avec_site_veillot / avec_site_recent
    veillot_signals     TEXT,
    recent_signals      TEXT,
    copyright_year      TEXT,
    fetch_error         TEXT,
    -- Pipeline CRM
    stage               TEXT NOT NULL DEFAULT 'a_contacter',
    interet             INTEGER,                              -- 1-5
    notes               TEXT,
    last_contacted_at   TIMESTAMPTZ,
    next_action         TEXT,
    next_action_due     TIMESTAMPTZ,
    -- Métadonnées
    source              TEXT DEFAULT 'rocketreach',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospects_stage ON prospects(stage);
CREATE INDEX IF NOT EXISTS idx_prospects_cat   ON prospects(categorie);
CREATE INDEX IF NOT EXISTS idx_prospects_email ON prospects(email);

-- ── Audits ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audits (
    id              BIGSERIAL PRIMARY KEY,
    prospect_id     BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    final_url       TEXT,
    https           BOOLEAN,
    tls_version     TEXT,
    security_grade  TEXT,
    technos         TEXT,
    veillot_tags    TEXT,
    title           TEXT,
    description     TEXT,
    h1              TEXT,
    copyright_year  INTEGER,
    html_size_kb    REAL,
    image_count     INTEGER,
    modern_image_count INTEGER,
    findings        TEXT,
    raw_data        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audits_prospect ON audits(prospect_id);

-- ── Calls (sessions cold call) ───────────────────────────────
CREATE TABLE IF NOT EXISTS calls (
    id              BIGSERIAL PRIMARY KEY,
    prospect_id     BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    call_number     INTEGER NOT NULL DEFAULT 1,
    state           TEXT,
    statut          TEXT,
    summary         TEXT,
    next_action     TEXT,
    rdv2_date       TEXT,
    rdv2_heure      TEXT,
    interet         INTEGER,
    roi_valeur_client    REAL,
    roi_leads            REAL,
    roi_conversion       REAL,
    roi_devis            REAL,
    roi_gain_mensuel     REAL,
    roi_payback_mois     REAL,
    visuels_promis  TEXT,
    budget_recu     TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_calls_prospect ON calls(prospect_id);

-- ── Activities timeline ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS activities (
    id              BIGSERIAL PRIMARY KEY,
    prospect_id     BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    type            TEXT NOT NULL,
    title           TEXT,
    body            TEXT,
    metadata        TEXT,
    due_at          TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_act_prospect  ON activities(prospect_id);
CREATE INDEX IF NOT EXISTS idx_act_due       ON activities(due_at);

-- ── Emails (manuels + campagnes) ─────────────────────────────
CREATE TABLE IF NOT EXISTS emails (
    id              BIGSERIAL PRIMARY KEY,
    prospect_id     BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    sequence_step   TEXT NOT NULL DEFAULT 'manual',  -- manual / J0 / J+4 / J+10 / J+18 / custom
    from_email      TEXT,                             -- noreply@... ou user@mad-makers.fr
    from_name       TEXT,
    to_email        TEXT,
    reply_to        TEXT,
    subject         TEXT,
    body            TEXT,
    body_html       TEXT,                             -- version HTML rendue (avec footer RGPD)
    attachments_json TEXT,                            -- JSON list of {filename, size_kb}
    status          TEXT NOT NULL DEFAULT 'draft',    -- draft / scheduled / sent / failed / opened / replied
    scheduled_at    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    replied_at      TIMESTAMPTZ,
    resend_message_id TEXT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_prospect  ON emails(prospect_id);
CREATE INDEX IF NOT EXISTS idx_emails_status    ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_scheduled ON emails(scheduled_at) WHERE status = 'scheduled';

-- ── Unsubscribes (RGPD : opt-out global par email) ──────────
CREATE TABLE IF NOT EXISTS unsubscribes (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    prospect_id     BIGINT REFERENCES prospects(id) ON DELETE SET NULL,
    reason          TEXT,
    user_agent      TEXT,
    unsubscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unsubs_email ON unsubscribes(email);

-- ── Email templates (bibliothèque réutilisable) ─────────────
CREATE TABLE IF NOT EXISTS email_templates (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT,                     -- cold_email / follow_up / breakup / custom
    segment         TEXT,                     -- A_SANS_SITE / B_DG / C_DAF / D_MARKETING / GENERIC
    step            TEXT,                     -- J0 / J+4 / J+10 / J+18 / custom
    subject         TEXT NOT NULL,
    body_html       TEXT NOT NULL,
    variables_used  TEXT,                     -- JSON list ex: ["prenom","entreprise","site_url"]
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tpls_segment ON email_templates(segment);
CREATE INDEX IF NOT EXISTS idx_tpls_step    ON email_templates(step);
CREATE INDEX IF NOT EXISTS idx_tpls_active  ON email_templates(is_archived);
