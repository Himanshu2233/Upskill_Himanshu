# database.py — SQLite database operations
#
# We use sqlite3 which is BUILT INTO Python (no pip install).
# It stores all passwords in a single file: passwords.db
#
# Database structure (2 tables):
#
# TABLE: master
#   id | salt (bytes) | verification_token (bytes)
#   → Stores the salt used to derive the key, and a test token
#     to verify the master password at login.
#
# TABLE: passwords
#   id | service | username | encrypted_password | notes
#   → Stores each saved password entry. The password column
#     contains encrypted bytes, NOT plain text.

import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'passwords.db')


def get_connection():
    """Opens (or creates) the SQLite database file."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row   # Makes rows behave like dicts
    return conn


def initialize_db():
    """
    Creates tables if they don't exist yet.
    Called once when the app starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master (
            id                  INTEGER PRIMARY KEY,
            salt                BLOB NOT NULL,
            verification_token  BLOB NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passwords (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            service             TEXT NOT NULL,
            username            TEXT NOT NULL,
            encrypted_password  BLOB NOT NULL,
            notes               TEXT DEFAULT ""
        )
    ''')

    conn.commit()
    conn.close()


def is_master_set() -> bool:
    """Returns True if a master password has been set up already."""
    conn = get_connection()
    row = conn.execute('SELECT COUNT(*) FROM master').fetchone()
    conn.close()
    return row[0] > 0


def save_master(salt: bytes, verification_token: bytes):
    """Saves the master password's salt and verification token."""
    conn = get_connection()
    conn.execute('DELETE FROM master')   # Only one master allowed
    conn.execute('INSERT INTO master (salt, verification_token) VALUES (?, ?)',
                 (salt, verification_token))
    conn.commit()
    conn.close()


def get_master() -> tuple:
    """Returns (salt, verification_token) for the stored master password."""
    conn = get_connection()
    row = conn.execute('SELECT salt, verification_token FROM master').fetchone()
    conn.close()
    return bytes(row['salt']), bytes(row['verification_token'])


def add_password(service: str, username: str, encrypted_password: bytes, notes: str = ''):
    """Inserts a new password entry into the database."""
    conn = get_connection()
    conn.execute(
        'INSERT INTO passwords (service, username, encrypted_password, notes) VALUES (?, ?, ?, ?)',
        (service, username, encrypted_password, notes)
    )
    conn.commit()
    conn.close()


def get_all_passwords() -> list:
    """Returns all saved password entries (still encrypted)."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT id, service, username, encrypted_password, notes FROM passwords ORDER BY service'
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_password(entry_id: int):
    """Deletes a password entry by its ID."""
    conn = get_connection()
    conn.execute('DELETE FROM passwords WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()


def search_passwords(query: str) -> list:
    """Searches by service or username (case-insensitive)."""
    conn = get_connection()
    like = f'%{query}%'
    rows = conn.execute(
        'SELECT id, service, username, encrypted_password, notes FROM passwords '
        'WHERE service LIKE ? OR username LIKE ? ORDER BY service',
        (like, like)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
