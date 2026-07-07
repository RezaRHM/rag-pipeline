"""
db/connection.py
─────────────────────────────────────────────────────────
اتصال مرکزی به PostgreSQL و Qdrant.
همه ماژول‌های دیگه از اینجا import می‌کنن —
تا اتصال‌ها یه‌جا تعریف بشن، نه تکراری.
─────────────────────────────────────────────────────────
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

PG_HOST     = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
PG_DB       = os.getenv("POSTGRES_DB", "ragdb")
PG_USER     = os.getenv("POSTGRES_USER", "raguser")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ragpass123")


def get_qdrant() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_postgres():
    """یه connection جدید به PostgreSQL برمی‌گردونه"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        cursor_factory=RealDictCursor
    )