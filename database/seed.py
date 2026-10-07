"""Replay the original demo records using Python, with fresh password salts."""

import hashlib
import hmac
import json
import secrets
from pathlib import Path

from . import check_database, table_counts, transaction

DEMO_PASSWORD = 'GuitarDemo!2026'


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64)
    return f'scrypt$16384$8$1${salt}${digest.hex()}'


def verify_password(password, encoded):
    try:
        algorithm, n, r, p, salt, digest = encoded.split('$')
        if algorithm != 'scrypt' or (int(n), int(r), int(p)) != (16384, 8, 1):
            return False
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=int(n), r=int(r), p=int(p), dklen=64)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False


def seed_demo(db):
    operations = json.loads((Path(__file__).parent / 'demo-data.json').read_text(encoding='utf-8'))
    with transaction(db):
        counts = table_counts(db)
        if len(counts) != 20:
            raise ValueError('Initialize the expected 20-table schema before seeding.')
        if any(row['rows'] for row in counts):
            raise ValueError('Demo seed requires empty tables. Existing data was preserved. Use SHOP_DB_PATH for a separate demo database.')
        for operation in operations:
            parameters = [password_hash(DEMO_PASSWORD) if value == '__DEMO_PASSWORD_HASH__' else value
                          for value in operation['parameters']]
            db.execute(operation['sql'], parameters)
        counts = check_database(db)
        if any(row['rows'] != 10 for row in counts):
            raise ValueError('Demo must contain exactly 10 rows per table.')
        return counts
