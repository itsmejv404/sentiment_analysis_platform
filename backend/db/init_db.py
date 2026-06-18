import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from backend import config
from backend.db.db import engine, Base
import backend.db.models as models  # Import models to ensure they are registered with Base

def init_db():
    print("Starting Database Initialization...")
    url = config.DATABASE_URL
    if not url.startswith("postgresql://"):
        print("Invalid DATABASE_URL format. Expected postgresql://...")
        return

    try:
        # Split into connection part and database name
        # We handle cases where there might be multiple slashes (unlikely for PG URL but safe)
        parts = url.rsplit("/", 1)
        base_conn_url = parts[0]
        db_name = parts[1]
        
        # Connect to 'postgres' default database to check/create the target database
        # We need a connection that can run CREATE DATABASE (cannot be in a transaction block)
        admin_conn_str = f"{base_conn_url}/postgres"
        
        print(f"Connecting to admin database: {base_conn_url}/postgres")
        conn = psycopg2.connect(admin_conn_str)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone()
            
            if not exists:
                print(f"Creating database '{db_name}'...")
                cur.execute(f"CREATE DATABASE {db_name}")
            else:
                print(f"Database '{db_name}' already exists.")
        
        conn.close()
    except Exception as e:
        print(f"Note: Could not verify/create database via admin connection: {e}")
        print("Continuing to table creation (assuming database might already exist)...")

    print("Creating tables and applying schema...")
    try:
        Base.metadata.create_all(engine)
        print("All tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"Error creating tables: {e}")
        return

    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
