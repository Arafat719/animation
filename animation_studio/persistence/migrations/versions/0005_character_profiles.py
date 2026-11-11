"""Immutable explicit character profile snapshots; legacy character rows unchanged."""

from alembic import op

revision = '0005_character_profiles'
down_revision = '0004_plan_approval'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.exec_driver_sql("""
        CREATE TABLE character_profiles (
            character_id INTEGER PRIMARY KEY REFERENCES characters(id),
            schema_version INTEGER NOT NULL CHECK (schema_version = 1),
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.exec_driver_sql("""
        CREATE TRIGGER character_profiles_no_update
        BEFORE UPDATE ON character_profiles BEGIN
            SELECT RAISE(ABORT, 'Character profile is immutable');
        END
    """)


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
