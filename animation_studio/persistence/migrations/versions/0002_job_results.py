"""Add immutable provider outcomes without rewriting existing job rows."""

from alembic import op

revision = '0002_job_results'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql('''
        CREATE TABLE job_results (
            job_id INTEGER PRIMARY KEY NOT NULL REFERENCES render_jobs(id) ON DELETE RESTRICT,
            schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version = 1),
            result_json TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (result_json IS NOT NULL AND error_code IS NULL AND error_message IS NULL)
                OR
                (result_json IS NULL AND error_code IS NOT NULL AND length(trim(error_code)) > 0
                 AND error_message IS NOT NULL AND length(trim(error_message)) > 0)
            )
        )
    ''')


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
