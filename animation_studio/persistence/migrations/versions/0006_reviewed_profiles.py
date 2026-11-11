"""Add reviewed v2 storage without rewriting immutable v1 snapshots."""

from alembic import op

revision = '0006_reviewed_profiles'
down_revision = '0005_character_profiles'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.exec_driver_sql("""
        CREATE TABLE reviewed_character_profiles (
            character_id INTEGER PRIMARY KEY REFERENCES characters(id),
            schema_version INTEGER NOT NULL CHECK (schema_version = 2),
            reviewed_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            reviewed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
    """)
    connection.exec_driver_sql("""
        CREATE TRIGGER reviewed_character_profiles_no_update
        BEFORE UPDATE ON reviewed_character_profiles BEGIN
            SELECT RAISE(ABORT, 'Character profile is immutable');
        END
    """)
    # Guard both tables and the same table, including INSERT OR REPLACE writers.
    for table in ('character_profiles', 'reviewed_character_profiles'):
        connection.exec_driver_sql(f"""
            CREATE TRIGGER {table}_single_profile
            BEFORE INSERT ON {table}
            WHEN EXISTS (SELECT 1 FROM character_profiles WHERE character_id=NEW.character_id)
              OR EXISTS (SELECT 1 FROM reviewed_character_profiles WHERE character_id=NEW.character_id)
            BEGIN
                SELECT RAISE(ABORT, 'Character profile already saved');
            END
        """)


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; restore a verified backup instead.')
