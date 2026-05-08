-- ============================================================
-- Mad Makers CRM — schéma SQLite
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ── Prospects (table maître) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS prospects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_complet         TEXT NOT NULL,
    prenom              TEXT,
    nom                 TEXT,
    titre               TEXT,
    entreprise          TEXT,
    ville               TEXT,
    email               TEXT,
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
    stage               TEXT NOT NULL DEFAULT 'a_contacter',  -- a_contacter / email_envoye / en_relance / rdv_1_cale / rdv_1_fait / rdv_2_cale / rdv_2_fait / devis_envoye / signe / perdu / dormant
    interet             INTEGER,                              -- 1-5
    notes               TEXT,
    last_contacted_at   TIMESTAMP,
    next_action         TEXT,
    next_action_due     TIMESTAMP,
    -- Métadonnées
    source              TEXT DEFAULT 'rocketreach',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prospects_stage ON prospects(stage);
CREATE INDEX IF NOT EXISTS idx_prospects_cat   ON prospects(categorie);
CREATE INDEX IF NOT EXISTS idx_prospects_email ON prospects(email);

-- ── Audits (un par site, dernier en date utilisé) ────────────
CREATE TABLE IF NOT EXISTS audits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id     INTEGER NOT NULL,
    final_url       TEXT,
    https           INTEGER,        -- bool
    tls_version     TEXT,
    security_grade  TEXT,           -- A-F
    technos         TEXT,           -- comma-separated
    veillot_tags    TEXT,           -- comma-separated
    title           TEXT,
    description     TEXT,
    h1              TEXT,
    copyright_year  INTEGER,
    html_size_kb    REAL,
    image_count     INTEGER,
    modern_image_count INTEGER,
    findings        TEXT,           -- newline-separated security findings
    raw_data        TEXT,           -- full JSON dump
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audits_prospect ON audits(prospect_id);

-- ── Calls (sessions cold call) ───────────────────────────────
CREATE TABLE IF NOT EXISTS calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id     INTEGER NOT NULL,
    call_number     INTEGER NOT NULL DEFAULT 1,    -- 1 ou 2
    state           TEXT,                          -- JSON form state
    statut          TEXT,                          -- RDV 2 calé / À relancer / Pas intéressé / etc.
    summary         TEXT,                          -- résumé express
    next_action     TEXT,
    rdv2_date       TEXT,
    rdv2_heure      TEXT,
    interet         INTEGER,
    -- ROI calculé
    roi_valeur_client    REAL,
    roi_leads            REAL,
    roi_conversion       REAL,
    roi_devis            REAL,
    roi_gain_mensuel     REAL,
    roi_payback_mois     REAL,
    -- Visuels
    visuels_promis  TEXT,
    budget_recu     TEXT,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calls_prospect ON calls(prospect_id);

-- ── Activities timeline ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS activities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id     INTEGER NOT NULL,
    type            TEXT NOT NULL,    -- call / email / meeting / note / stage_change / audit
    title           TEXT,
    body            TEXT,
    metadata        TEXT,             -- JSON freeform
    due_at          TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_act_prospect  ON activities(prospect_id);
CREATE INDEX IF NOT EXISTS idx_act_due       ON activities(due_at);

-- ── Emails (sequences) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id     INTEGER NOT NULL,
    sequence_step   TEXT NOT NULL,   -- J0 / J+4 / J+10 / J+18 / custom
    subject         TEXT,
    body            TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft / scheduled / sent / opened / replied
    scheduled_at    TIMESTAMP,
    sent_at         TIMESTAMP,
    opened_at       TIMESTAMP,
    replied_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_emails_prospect ON emails(prospect_id);
CREATE INDEX IF NOT EXISTS idx_emails_status   ON emails(status);
