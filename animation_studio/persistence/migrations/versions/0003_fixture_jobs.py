"""Persist runner ownership separately from legacy demo job rows."""

from alembic import op

revision = '0003_fixture_jobs'
down_revision = '0002_job_results'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql('''
        CREATE TABLE fixture_jobs (
            job_id INTEGER PRIMARY KEY NOT NULL REFERENCES render_jobs(id) ON DELETE RESTRICT
        )
    ''')


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
