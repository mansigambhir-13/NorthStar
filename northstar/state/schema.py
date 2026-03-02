"""SQLite schema for NorthStar state persistence."""

SCHEMA_VERSION = 1

CREATE_TABLES = """
-- Goals table
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    deadline TEXT,
    success_criteria TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    status TEXT DEFAULT 'pending',
    goal_id TEXT,
    goal_alignment REAL DEFAULT 0.0,
    impact INTEGER DEFAULT 50,
    urgency TEXT DEFAULT 'normal',
    effort_hours REAL DEFAULT 1.0,
    blocks TEXT DEFAULT '[]',
    leverage_score REAL DEFAULT 0.0,
    reasoning TEXT DEFAULT '',
    file_path TEXT,
    line_number INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

-- Priority Debt Scores table
CREATE TABLE IF NOT EXISTS pds_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score REAL NOT NULL,
    severity TEXT NOT NULL,
    top_contributors TEXT DEFAULT '[]',
    diagnosis TEXT DEFAULT '',
    recommendations TEXT DEFAULT '[]',
    calculated_at TEXT NOT NULL
);

-- Decision events table
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    task_id TEXT,
    task_title TEXT DEFAULT '',
    from_task_id TEXT,
    to_task_id TEXT,
    leverage_score REAL,
    reason TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}'
);

-- Drift alerts table
CREATE TABLE IF NOT EXISTS drift_alerts (
    id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    current_task_id TEXT,
    current_task_title TEXT DEFAULT '',
    current_leverage REAL DEFAULT 0.0,
    top_task_id TEXT,
    top_task_title TEXT DEFAULT '',
    top_leverage REAL DEFAULT 0.0,
    drift_ratio REAL DEFAULT 0.0,
    session_minutes REAL DEFAULT 0.0,
    message TEXT DEFAULT '',
    user_response TEXT,
    snoozed_until TEXT,
    created_at TEXT NOT NULL
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes REAL DEFAULT 0.0,
    tasks_started TEXT DEFAULT '[]',
    tasks_completed TEXT DEFAULT '[]',
    drift_alerts INTEGER DEFAULT 0,
    pds_start REAL DEFAULT 0.0,
    pds_end REAL DEFAULT 0.0
);

-- Config key-value table
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id);
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
CREATE INDEX IF NOT EXISTS idx_decisions_event_type ON decisions(event_type);
CREATE INDEX IF NOT EXISTS idx_pds_history_calculated_at ON pds_history(calculated_at);
CREATE INDEX IF NOT EXISTS idx_drift_alerts_created_at ON drift_alerts(created_at);
"""
