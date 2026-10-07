"""SQLite access and CLI commands for the Flask application."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import click
from flask import current_app, g

DEFAULT_DATABASE = Path(__file__).parent / 'data' / 'roels-guitar-shop.sqlite'
SCHEMA_VERSION = 1


def open_database(path):
    if str(path) != ':memory:':
        Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA busy_timeout = 5000')
    if str(path) != ':memory:':
        db.execute('PRAGMA journal_mode = WAL')
        db.execute('PRAGMA synchronous = FULL')
    return db


@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield db
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise


def initialize_database(db):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version == SCHEMA_VERSION:
        return
    if version != 0:
        raise ValueError(f'Unsupported schema version {version}; expected {SCHEMA_VERSION}.')
    if table_counts(db):
        raise ValueError('Refusing to initialize an unversioned database containing tables.')
    schema = (Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8')
    try:
        db.executescript('BEGIN IMMEDIATE;\n' + schema + '\nCOMMIT;')
    except Exception:
        if db.in_transaction:
            db.rollback()
        raise


def table_counts(db):
    tables = db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [{'table': row[0], 'rows': db.execute('SELECT count(*) FROM "' + row[0].replace('"', '""') + '"').fetchone()[0]}
            for row in tables.fetchall()]


def check_database(db):
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('Expected schema version 1. Run flask --app app db-init first.')
    if [row[0] for row in db.execute('PRAGMA integrity_check')] != ['ok']:
        raise ValueError('Database integrity check failed.')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Foreign key violations detected.')
    if db.execute('SELECT id FROM product_inventory WHERE stock_quantity < 0').fetchone():
        raise ValueError('Negative stock detected.')
    return table_counts(db)


def get_db():
    if 'db' not in g:
        g.db = open_database(current_app.config['DATABASE'])
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_setting(db, key, default=None):
    row = db.execute('SELECT value_json FROM settings WHERE key = ?', (key,)).fetchone()
    return json.loads(row[0]) if row else default


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command('db-init')
    def init_command():
        """Initialize the schema without overwriting existing data."""
        initialize_database(get_db())
        click.echo('Database initialized.')

    @app.cli.command('db-seed')
    def seed_command():
        """Insert the original demo dataset into an empty database."""
        from .seed import seed_demo
        try:
            seed_demo(get_db())
        except ValueError as error:
            raise click.ClickException(str(error)) from error
        click.echo('Demo seeded: 20 tables, 10 records each.')

    @app.cli.command('db-check')
    def check_command():
        """Check integrity, foreign keys, stock, and row counts."""
        for row in check_database(get_db()):
            click.echo(f"{row['table']}: {row['rows']}")
        click.echo('Integrity and foreign keys: OK.')
