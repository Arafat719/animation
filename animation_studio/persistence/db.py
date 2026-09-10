import os
import sqlite3
import threading
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

from animation_studio.settings import get_database_path


# Alembic uses module-level proxies; serialize in-process migration runs.
# BEGIN IMMEDIATE additionally serializes writers across processes.
_MIGRATION_LOCK = threading.Lock()


def init_db(db_path: str | None = None) -> str:
    target_path = get_database_path(db_path)
    directory = os.path.dirname(target_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    config = Config()
    config.set_main_option(
        'script_location', str(Path(__file__).parent / 'migrations').replace('%', '%%')
    )
    engine = create_engine(
        'sqlite+pysqlite://',
        creator=lambda: sqlite3.connect(target_path, isolation_level=None, timeout=30),
        poolclass=NullPool,
    )

    @event.listens_for(engine, 'begin')
    def begin_transaction(connection):
        connection.exec_driver_sql('BEGIN IMMEDIATE')

    try:
        with _MIGRATION_LOCK:
            with engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
    finally:
        engine.dispose()

    return target_path
