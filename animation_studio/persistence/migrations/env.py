"""Run migrations on the transaction supplied by init_db."""

from alembic import context

connection = context.config.attributes.get('connection')
if connection is None:
    raise RuntimeError('Run migrations through animation_studio.persistence.db.init_db.')

context.configure(connection=connection, target_metadata=None, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
