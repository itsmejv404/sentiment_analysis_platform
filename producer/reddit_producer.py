import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv
import redis
import urllib.parse
import requests
import logging
from bs4 import BeautifulSoup
import re
from psycopg2 import pool

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Redis credentials and initialization
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Database credentials and configuration
DB_NAME = os.getenv("DATABASE_NAME", "social_db")
DB_USER = os.getenv("DATABASE_USER", "postgres")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_PORT = os.getenv("DATABASE_PORT", "5432")

if not DB_PASSWORD:
    raise RuntimeError("DATABASE_PASSWORD environment variable is not configured in .env")

try:
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

FETCH_INTERVAL = 60
DEDUP_TTL = 3600 * 24     

def clean_rss_text(html_text):
    if not html_text: return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ")
    return text.strip()

def extract_post_id(link):
    match = re.search(r'/comments/([^/]+)/', link)
    if match: return match.group(1)
    return link.split('/')[-3] if len(link.split('/')) >= 3 else str(int(time.time()))

logger.info("Starting Resilient Reddit RSS Producer...")

def get_active_keywords():
    """
    Retrieve unique search keywords for all active tenants.
    Only keywords from tenants with active status and users having >= 100 credits are retrieved.
    This prevents processing posts for organizations with exhausted credits.
    """
    conn = db_pool.getconn()
    all_keywords = set()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.keywords
                FROM tenants t
                JOIN users u ON u.id = t.owner_id
                WHERE t.keywords IS NOT NULL
                  AND t.is_active = TRUE
                  AND COALESCE(u.credits, 0) >= 100
                """
            )
            for (keys_csv,) in cur.fetchall():
                for k in keys_csv.split(","):
                    k_str = k.strip()
                    if k_str: all_keywords.add(k_str)
    except Exception as e:
        logger.error(f"Failed pulling keywords: {e}")
    finally:
        db_pool.putconn(conn)
    return list(all_keywords)

# Continuous loop querying Reddit's JSON search endpoint for active keywords
while True:
    active_keywords = get_active_keywords()
    if not active_keywords:
        logger.info("No active tenant keywords found. Sleeping without fetching data.")
        time.sleep(FETCH_INTERVAL)
        continue

    for keyword in active_keywords:
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            url = f"https://www.reddit.com/search.json?q={encoded_keyword}&sort=new"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 SMSA Data Ingestion Worker/1.0'}
            response = requests.get(url, headers=headers, timeout=15)
            
            # Handle rate limiting (429 Too Many Requests) by backing off
            if response.status_code == 429:
                logger.warning(f"Rate limited by Reddit for {keyword}. Backing off for 120s...")
                time.sleep(120)
                continue
            elif response.status_code == 403:
                logger.error(f"Failed pulling {keyword} - 403 Forbidden. Check User-Agent or network.")
                continue
            elif response.status_code != 200:
                logger.error(f"Unexpected status {response.status_code} for {keyword}")
                continue

            try:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
            except ValueError:
                logger.error(f"Invalid JSON received for {keyword}")
                continue

            for post in posts:
                post_data = post.get("data", {})
                post_id = post_data.get("id")
                
                # Fallback to current timestamp if post ID is missing
                if not post_id:
                    post_id = str(int(time.time()))
                    
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                raw_content = f"{title} {selftext}"
                
                content = clean_rss_text(raw_content)
                if not content or len(content) < 10: continue 

                # De-duplicate posts at the ingestion layer using a Redis TTL key
                dedup_key = f"post:{post_id}"
                if not r.exists(dedup_key):
                    r.set(dedup_key, 1, ex=DEDUP_TTL)
                    
                    post_time = post_data.get("created_utc", time.time())
                    ups = post_data.get("ups", 0) or 0
                    num_comments = post_data.get("num_comments", 0) or 0
                    engagement = ups + num_comments
                        
                    # Structure the payload: [post_id, content, post_time, retry_count, engagement]
                    payload = [post_id, content, post_time, 0, engagement]
                    
                    try:
                        r.lpush("tweet_queue", json.dumps(payload))
                        logger.info(f"Produced to Queue: {post_id} for keyword '{keyword}' (engagement={engagement})")
                    except redis.RedisError as re_err:
                        logger.error(f"Redis queue failure: {re_err}")
                        
            # Sleep between keyword requests to mitigate aggressive rate limits
            time.sleep(5) 
        except Exception as e:
            logger.error(f"Critical error fetching '{keyword}': {e}", exc_info=True)
            time.sleep(10)

    logger.info(f"Cycle complete. Sleeping for {FETCH_INTERVAL} seconds...")
    time.sleep(FETCH_INTERVAL)