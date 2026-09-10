"""Create the initial tables or adopt the compatible unversioned schema."""

import sqlite3

from alembic import op

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

# Freeze this baseline; subsequent schema changes belong in new revisions.
TABLES = {
    'projects': """
        CREATE TABLE projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        master_prompt TEXT,
        target_duration_seconds INTEGER,
        status TEXT DEFAULT 'draft'
        )
    """,
    'characters': """
        CREATE TABLE characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        reference_image_paths TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'voices': """
        CREATE TABLE voices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        voice_type TEXT NOT NULL,
        language TEXT,
        style TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'shots': """
        CREATE TABLE shots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        order_index INTEGER NOT NULL,
        duration_seconds REAL NOT NULL,
        prompt TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
        )
    """,
    'render_jobs': """
        CREATE TABLE render_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        current_step TEXT,
        current_shot INTEGER,
        state TEXT DEFAULT 'queued',
        progress INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
}


def upgrade():
    connection = op.get_bind()
    # Compare SQLite's own column descriptions rather than merely stamping
    # arbitrary existing tables as compatible. All names below are constants.
    expected = sqlite3.connect(':memory:')
    try:
        for name, ddl in TABLES.items():
            expected.execute(ddl)
            existing = connection.exec_driver_sql(
                'SELECT type FROM sqlite_master WHERE name = ?', (name,)
            ).fetchone()
            if existing is None:
                connection.exec_driver_sql(ddl)
                continue
            actual_columns = [tuple(row) for row in connection.exec_driver_sql(
                f'PRAGMA table_info("{name}")'
            )]
            expected_columns = expected.execute(f'PRAGMA table_info("{name}")').fetchall()
            if existing[0] != 'table' or actual_columns != expected_columns:
                raise RuntimeError(
                    f'Incompatible legacy table: {name}. '
                    'Migration rolled back; inspect the schema before retrying.'
                )
    finally:
        expected.close()


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
