"""Versioned mock plans and approval bound to the saved revision."""

from alembic import op

revision = '0004_plan_approval'
down_revision = '0003_fixture_jobs'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql("""
        CREATE TABLE project_plans (
            project_id INTEGER PRIMARY KEY REFERENCES projects(id),
            revision INTEGER NOT NULL CHECK (revision > 0),
            plan_json TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
            result_json TEXT
        )
    """)


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
