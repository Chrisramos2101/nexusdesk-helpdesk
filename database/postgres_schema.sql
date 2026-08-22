CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    department TEXT DEFAULT '',
    email TEXT DEFAULT '',
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT DEFAULT '',
    last_login TEXT DEFAULT '',
    last_logout TEXT DEFAULT '',
    mfa_enabled INTEGER DEFAULT 0,
    mfa_secret TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    issue TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    closed_at TEXT DEFAULT '',
    assigned_to TEXT DEFAULT 'Unassigned',
    completed_by TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    category TEXT DEFAULT 'Other',
    sla_due_at TEXT DEFAULT '',
    submitted_by TEXT DEFAULT '',
    resolution_time TEXT DEFAULT '',
    sla_met TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS login_events (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_notes (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_attachments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mfa_codes (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    attempts INTEGER DEFAULT 0
);

ALTER TABLE mfa_codes
ADD COLUMN IF NOT EXISTS attempts INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS security_rate_limits (
    id SERIAL PRIMARY KEY,
    bucket_key TEXT NOT NULL,
    action TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    window_start TEXT NOT NULL,
    UNIQUE(bucket_key, action)
);

CREATE TABLE IF NOT EXISTS article_feedback (
    id SERIAL PRIMARY KEY,
    article_slug TEXT NOT NULL,
    username TEXT NOT NULL,
    was_helpful TEXT NOT NULL,
    feedback TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS article_views (
    id SERIAL PRIMARY KEY,
    article_slug TEXT NOT NULL,
    username TEXT NOT NULL,
    viewed_at TEXT NOT NULL
);
