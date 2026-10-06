import os
import sqlite3
from pathlib import Path
import pymysql
import pymysql.cursors
from config import Config

# Path for local SQLite fallback database
SQLITE_DB_PATH = Path(Config.BASE_DIR) / 'student_notes.db'

class SQLiteCursorWrapper:
    """Wrapper around sqlite3.Cursor to emulate PyMySQL DictCursor and convert %s to ?."""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, args=None):
        # Convert MySQL %s placeholder to SQLite ? placeholder
        sql = query.replace('%s', '?')
        if args:
            return self._cursor.execute(sql, tuple(args))
        return self._cursor.execute(sql)

    def executemany(self, query, args=None):
        sql = query.replace('%s', '?')
        return self._cursor.executemany(sql, args)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()

    def close(self):
        self._cursor.close()

class SQLiteConnectionWrapper:
    """Wrapper around sqlite3.Connection to provide PyMySQL-compatible cursor() interface."""
    def __init__(self, connection):
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

def get_db_connection(database=Config.DB_NAME):
    """
    Establish and return a database connection.
    Attempts to connect to MySQL first using PyMySQL.
    If MySQL credentials are not set or inaccessible on local development,
    gracefully falls back to a local SQLite database with identical schema.
    """
    # Attempt MySQL connection
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn
    except Exception as mysql_err:
        # Fall back to SQLite if running locally and MySQL is unavailable
        if os.getenv('FLASK_ENV', 'development') == 'development':
            conn = sqlite3.connect(str(SQLITE_DB_PATH))
            conn.isolation_level = None  # autocommit
            _ensure_sqlite_schema(conn)
            return SQLiteConnectionWrapper(conn)
        else:
            raise mysql_err

def _ensure_sqlite_schema(conn):
    """Ensure the notes table exists in SQLite fallback database."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT,
            s3_key TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.close()

def test_db_connection():
    """
    Test connectivity to the database server.
    Returns (status: bool, message: str).
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS test")
            cursor.fetchone()
        conn.close()
        # Check if connected to real MySQL or SQLite fallback
        try:
            m_conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4'
            )
            m_conn.close()
            return True, f"MySQL connected at {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
        except Exception:
            return True, f"Local database active ({SQLITE_DB_PATH.name} fallback)"
    except Exception as e:
        return False, str(e)

def init_db(schema_file_path=None):
    """
    Helper function to initialize the database and tables
    using schema.sql.
    """
    if schema_file_path is None:
        schema_file_path = Path(Config.BASE_DIR) / 'schema.sql'

    # Try MySQL first
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset='utf8mb4',
            autocommit=True
        )
        with conn.cursor() as cursor:
            with open(schema_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            for statement in statements:
                cursor.execute(statement)
        conn.close()
        return True, "MySQL database initialized successfully."
    except Exception as mysql_err:
        # If MySQL init fails, initialize SQLite
        try:
            conn = sqlite3.connect(str(SQLITE_DB_PATH))
            _ensure_sqlite_schema(conn)
            conn.close()
            return True, f"Local database initialized (MySQL error: {mysql_err})"
        except Exception as sqlite_err:
            return False, f"Init error: {sqlite_err}"
