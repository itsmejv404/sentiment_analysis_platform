from backend import config
import psycopg2

# Database schema migrations for social_db.
# This script applies updates such as adding columns and tables needed for tracking engagement metrics and alert logs.
conn = psycopg2.connect(
    dbname=config.DATABASE_NAME,
    user=config.DATABASE_USER,
    password=config.DATABASE_PASSWORD,
    host=config.DATABASE_HOST,
    port=config.DATABASE_PORT
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("ALTER TABLE product_sentiments ADD COLUMN IF NOT EXISTS engagement INTEGER DEFAULT 0;")
    print("Added engagement column.")
    cur.execute("ALTER TABLE users ALTER COLUMN credits SET DEFAULT 500;")
    print("Updated users.credits default to 500.")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_alert_logs (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id),
            alert_type VARCHAR,
            triggered_at TIMESTAMP DEFAULT NOW()
        );
    """)
    print("Created tenant_alert_logs table.")
conn.close()
print("Migration complete.")
