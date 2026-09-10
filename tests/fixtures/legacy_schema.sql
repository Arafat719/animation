-- Snapshot of the pre-migration schema, 2026-09-07. Keep independent of migrations.

CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                master_prompt TEXT,
                target_duration_seconds INTEGER,
                status TEXT DEFAULT 'draft'
            );

CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                reference_image_paths TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS voices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                voice_type TEXT NOT NULL,
                language TEXT,
                style TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS shots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                order_index INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            );

CREATE TABLE IF NOT EXISTS render_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                current_step TEXT,
                current_shot INTEGER,
                state TEXT DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
