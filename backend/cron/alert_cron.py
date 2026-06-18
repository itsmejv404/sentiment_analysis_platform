
import time
import logging
import psycopg2
from psycopg2 import pool
from datetime import datetime, timedelta
from backend.celery.tasks import send_sentiment_alert
from backend.config import DATABASE_HOST, DATABASE_NAME, DATABASE_PORT, DATABASE_PASSWORD, DATABASE_USER
logging.basicConfig(level=logging.INFO, format="%(asctime)s [ALERT_CRON] %(message)s")
logger = logging.getLogger(__name__)

EVAL_INTERVAL = 60 * 10  # Re-evaluate every 10 minutes
ALERT_COOLDOWN_HOURS = 12  # Don't re-alert within this many hours

try:
    db_pool = pool.ThreadedConnectionPool(
        1, 5,
        dbname=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD,
        host=DATABASE_HOST, port=DATABASE_PORT
    )
    logger.info("Connected to PostgreSQL.")
except Exception as e:
    logger.error(f"CRITICAL: DB pool failed: {e}")
    exit(1)


def get_tenant_admins(conn, tenant_id):
    """Return a list of usernames (used as emails) for admins of the tenant."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.username
            FROM users u
            JOIN tenant_users tu ON tu.user_id = u.id
            WHERE tu.tenant_id = %s AND tu.role = 'admin'
            """,
            (tenant_id,)
        )
        return [row[0] for row in cur.fetchall()]


def already_alerted(conn, tenant_id, alert_type):
    """Check if this alert type was triggered recently (within cooldown window)."""
    cutoff = datetime.utcnow() - timedelta(hours=ALERT_COOLDOWN_HOURS)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM tenant_alert_logs WHERE tenant_id = %s AND alert_type = %s AND triggered_at > %s",
            (tenant_id, alert_type, cutoff)
        )
        return cur.fetchone() is not None


def log_alert(conn, tenant_id, alert_type):
    """Record that an alert was sent."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tenant_alert_logs (tenant_id, alert_type, triggered_at) VALUES (%s, %s, %s)",
            (tenant_id, alert_type, datetime.utcnow())
        )
    conn.commit()


def evaluate_tenants():
    conn = db_pool.getconn()
    try:
        window_start = datetime.utcnow() - timedelta(hours=12)

        # Get all tenants with brand names configured
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.brand_name
                FROM tenants t
                JOIN users u ON u.id = t.owner_id
                WHERE t.brand_name IS NOT NULL
                  AND t.is_active = TRUE
                  AND COALESCE(u.credits, 0) >= 100
                """
            )
            tenants = cur.fetchall()

        for tenant_id, brand_name in tenants:
            # Count sentiment breakdown over last 12 hours
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sentiment, content
                    FROM product_sentiments
                    WHERE tenant_id = %s AND post_createdat >= %s
                    """,
                    (tenant_id, window_start)
                )
                rows = cur.fetchall()

            if not rows:
                continue

            total = len(rows)
            pos_posts = [r for r in rows if r[0] == "POSITIVE"]
            neg_posts = [r for r in rows if r[0] == "NEGATIVE"]
            neu_count = total - len(pos_posts) - len(neg_posts)

            pos_pct = (len(pos_posts) / total) * 100
            neg_pct = (len(neg_posts) / total) * 100
            neu_pct = (neu_count / total) * 100

            breakdown = {
                "positive_pct": pos_pct,
                "negative_pct": neg_pct,
                "neutral_pct": neu_pct
            }
            timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            # Check thresholds
            alert_type = None
            sample_posts = []

            if neg_pct >= 70:
                alert_type = "HIGH_NEGATIVE"
                sample_posts = [r[1] for r in neg_posts[:5]]
            elif pos_pct >= 70:
                alert_type = "HIGH_POSITIVE"
                sample_posts = [r[1] for r in pos_posts[:5]]

            if alert_type:
                if already_alerted(conn, tenant_id, alert_type):
                    logger.info(f"Tenant {tenant_id} ({brand_name}): {alert_type} suppressed (cooldown active).")
                    continue

                # it will get the admin email of the tenant
                admin_emails = get_tenant_admins(conn, tenant_id)
                if not admin_emails:
                    logger.warning(f"Tenant {tenant_id}: no admins found, skipping alert.")
                    continue

                # if there are multple admins then it sends mail to all of them asyncly
                for email in admin_emails:
                    send_sentiment_alert.delay(email, brand_name, alert_type, breakdown, sample_posts, timestamp_str)
                    logger.info(f"[ALERT] Sent {alert_type} to {email} for '{brand_name}' (pos={pos_pct:.1f}%, neg={neg_pct:.1f}%)")

                log_alert(conn, tenant_id, alert_type)

    except Exception as e:
        logger.error(f"Error during evaluation: {e}", exc_info=True)
    finally:
        db_pool.putconn(conn)


logger.info(f"Alert cron started. Evaluating every {EVAL_INTERVAL // 60} minutes.")
while True:
    evaluate_tenants()
    time.sleep(EVAL_INTERVAL)
