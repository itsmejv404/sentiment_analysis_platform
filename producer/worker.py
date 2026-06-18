import json
import requests
import time
import os
from pathlib import Path
from dotenv import load_dotenv
import redis
import re
import emoji
import hashlib
from datetime import datetime, timezone
from psycopg2 import pool
import logging
from contextlib import contextmanager

# Load environment configuration from .env files in local or parent directories
BASE_DIR = Path(__file__).resolve().parent
ENV_CANDIDATES = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    BASE_DIR.parent / "backend" / ".env",
]

for env_path in ENV_CANDIDATES:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Redis configuration and initialization
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

AI_URL = os.getenv("ML_API_URL", "http://127.0.0.1:8001/analyze")
MAX_RETRIES = 3

# Database configuration and connection pool initialization
DB_NAME = os.getenv("DATABASE_NAME", "social_db")
DB_USER = os.getenv("DATABASE_USER", "postgres")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_PORT = os.getenv("DATABASE_PORT", "5432")

if not DB_PASSWORD:
    raise RuntimeError("DATABASE_PASSWORD environment variable is not configured in .env")

try:
    # Use ThreadedConnectionPool for safe, highly concurrent DB writes
    db_pool = pool.ThreadedConnectionPool(
        1, 10,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
except Exception as e:
    logger.error(f"CRITICAL: Error creating DB pool: {e}")
    exit(1)

@contextmanager
def get_db_connection():
    """Safely acquires and releases a database connection from the pool."""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)

def clean_and_format_text(text):
    """Cleans raw social media text for optimal AI processing."""
    text = emoji.demojize(text)
    text = re.sub(r"(\*|_)+", "", text) # Remove markdown
    text = re.sub(r"http\S+|www.\S+", "", text) # Strip URLs
    text = re.sub(r"\s+", " ", text).strip() # Normalize whitespace
    if len(text) > 1000: text = text[:1000] + "..." # Truncate safely
    return text

def send_to_dlq(post_id, payload, error_msg):
    """Routes failed posts to a Dead Letter Queue for later inspection."""
    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dead_letter_queue (post_id, payload, error_message) VALUES (%s, %s, %s)",
                    (post_id, json.dumps(payload), str(error_msg))
                )
            conn.commit()
            logger.warning(f"Sent Post {post_id} to Dead Letter Queue.")
        except Exception as e:
            conn.rollback()
            logger.error(f"CRITICAL: Failed to write to DLQ: {e}")

def get_post_comments(post_id: str, limit: int = 5) -> list[str]:
    """Fetches top comments to determine if a question has been answered by the crowd."""
    url = f"https://www.reddit.com/comments/{post_id}.json?sort=top&limit={limit}"
    headers = {"User-Agent": "DataPipelineWorker/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return []
            
        data = response.json()
        comments_list = data[1].get("data", {}).get("children", [])
        
        return [clean_and_format_text(c.get("data", {}).get("body", "")) 
                for c in comments_list if c.get("data", {}).get("body") not in [None, "[deleted]", "[removed]"]]
    except Exception as e:
        logger.error(f"Failed to fetch comments for {post_id}: {e}")
        return []

# --- Main Worker Loop ---
logger.info("Worker started. Listening to tweet_queue...")
while True:
    try:
        # Dequeue payload from Redis queue (blocking pop with 5s timeout)
        result = r.brpop("tweet_queue", timeout=5)
        if result is None: continue

        _, tweet_data = result
        payload_data = json.loads(tweet_data)
        
        post_id = payload_data[0]
        raw_tweet = payload_data[1]
        post_created = payload_data[2]
        retry_count = payload_data[3] if len(payload_data) >= 4 else 0
        engagement = payload_data[4] if len(payload_data) >= 5 else 0

        post_createdAt = datetime.fromtimestamp(post_created, tz=timezone.utc)
        tweet = clean_and_format_text(raw_tweet)
        tweet_lower = tweet.lower()
        
        # Deduplication: Generate unique SHA-256 content hash of normalized text
        content_hash = hashlib.sha256(tweet_lower.encode('utf-8')).hexdigest()

        # Query all currently active tenants who have sufficient credits (>= 100)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT t.id, t.brand_name, t.keywords
                    FROM tenants t
                    JOIN users u ON u.id = t.owner_id
                    WHERE t.brand_name IS NOT NULL
                      AND t.is_active = TRUE
                      AND COALESCE(u.credits, 0) >= 100
                    """
                )
                tenants = cur.fetchall()

        if not tenants:
            logger.info("No active tenants available. Skipping queued item without AI processing.")
            continue

        # Evaluate the post content against each active tenant's brand and keywords
        for tenant_id, tenant_brand, tenant_keywords_str in tenants:
            if not tenant_keywords_str:
                continue
                
            tenant_products = [k.strip() for k in tenant_keywords_str.split(",") if k.strip()]
            
            # Isolate which specific products or keywords are mentioned in the post
            mentioned_products = [p for p in tenant_products if p.lower() in tweet_lower]
            if not mentioned_products: 
                continue
            
            mentioned_features = mentioned_products # Use keywords as features for dynamic tenants

            for product in mentioned_products:
                payload = {"content": tweet, "target_brand": tenant_brand, "product": product, "features": mentioned_features}
                current_tenant_id = tenant_id

                # 1. Dispatch payload to the NLP Sentiment Analysis API
                try:
                    response = requests.post(AI_URL, json=payload, timeout=60)
                    response.raise_for_status()
                    data = response.json()
                except Exception as api_err:
                    retry_count += 1
                    # Enforce exponential backoff retries and DLQ routing on permanent failure
                    if retry_count >= MAX_RETRIES:
                        send_to_dlq(post_id, payload_data, api_err)
                    else:
                        backoff_time = 2 ** retry_count
                        logger.warning(f"API failed for {post_id}. Retrying in {backoff_time}s... ({retry_count}/{MAX_RETRIES})")
                        time.sleep(backoff_time)
                        r.lpush("tweet_queue", json.dumps([post_id, raw_tweet, post_created, retry_count]))
                    continue 

                # 2. Extract NLP Classification Results
                safety_status = data.get("safety_status", "SAFE")
                intent = data.get("intent", "NEUTRAL")
                sentiment = data.get("sentiment", "NEUTRAL")
                p_score = data.get("score", 0.0)
                is_sarcastic = data.get("is_sarcastic", False)
                feature_sentiments = data.get("feature_sentiments", {})
                keywords = data.get("keywords", [])
                is_crowd_sourced = False

                # 3. Crowd Consensus: Analyze top comments to check if community consensus has resolved the question
                if intent in ["QUESTION", "REQUEST"]:
                    comments = get_post_comments(post_id, limit=5)
                    if comments:
                        valid_comments = 0
                        
                        for comment_text in comments:
                            c_payload = {"content": comment_text, "target_brand": tenant_brand, "product": product, "features": mentioned_features}
                            try:
                                c_response = requests.post(AI_URL, json=c_payload, timeout=30)
                                if c_response.status_code == 200:
                                    c_data = c_response.json()
                                    if c_data.get("safety_status") == "SAFE" and c_data.get("sentiment") != "N/A":
                                        valid_comments += 1
                            except Exception:
                                continue 
                                
                        if valid_comments > 0:
                            is_crowd_sourced = True

                # 4. Save results to PostgreSQL using INSERT WHERE NOT EXISTS to prevent duplicates
                with get_db_connection() as conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO product_sentiments
                                    (post_id, tenant_id, product, content, intent, sentiment, overall_score, feature_sentiments, keywords, safety_status, is_sarcastic, is_crowd_sourced, post_createdat, content_hash, engagement)
                                SELECT
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                WHERE NOT EXISTS (
                                    SELECT 1
                                    FROM product_sentiments
                                    WHERE post_id = %s AND tenant_id = %s
                                );
                                """,
                                (
                                    post_id,
                                    current_tenant_id,
                                    product,
                                    tweet,
                                    intent,
                                    sentiment,
                                    p_score,
                                    json.dumps(feature_sentiments),
                                    json.dumps(keywords),
                                    safety_status,
                                    is_sarcastic,
                                    is_crowd_sourced,
                                    post_createdAt,
                                    content_hash,
                                    engagement,
                                    post_id,
                                    current_tenant_id,
                                )
                            )
                        conn.commit()
                        logger.info(f"Saved: {product.upper()} | Intent: {intent} | Sentiment: {sentiment} | Engagement: {engagement}")
                    except Exception as db_err:
                        conn.rollback()
                        logger.error(f"Database insertion error: {db_err}")

    except Exception as e:
        logger.error(f"Unexpected Worker Error: {e}", exc_info=True)
        time.sleep(5)