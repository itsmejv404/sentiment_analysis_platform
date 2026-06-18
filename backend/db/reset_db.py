import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from backend import config
from backend.db.db import engine, Base
import backend.db.models as models

def reset_db():
    print("Dropping database...")
    url = config.DATABASE_URL
    parts = url.rsplit("/", 1)
    base_conn_url = parts[0]
    db_name = parts[1]
    admin_conn_str = f"{base_conn_url}/postgres"
    conn = psycopg2.connect(admin_conn_str)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        # Disconnect all connections first
        cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();")
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cur.execute(f"CREATE DATABASE {db_name}")
    conn.close()
    
    print("Creating all tables from new schema...")
    Base.metadata.create_all(engine)
    print("Database reset complete.")

if __name__ == "__main__":
    reset_db()
