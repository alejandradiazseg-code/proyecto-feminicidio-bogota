"""
Módulo de conexión a PostgreSQL/PostGIS.
Lee credenciales desde .env y expone una función para obtener conexión.
"""
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


@contextmanager
def get_connection():
    """
    Context manager para obtener una conexión a PostgreSQL.
    Garantiza cierre limpio de conexión.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('UTF8')
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = None):
    """
    Ejecuta una consulta SELECT y devuelve todos los resultados como lista de diccionarios.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_one(query: str, params: tuple = None):
    """
    Ejecuta una consulta SELECT y devuelve un único resultado como diccionario.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()
