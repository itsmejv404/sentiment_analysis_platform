import json
import time
import uuid
import redis
import logging
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Redis connection (same as reddit_producer.py) ---
r = redis.Redis(host='localhost', port=6379, db=0)

DEDUP_TTL = 3600 * 24  # 24 hours, same as reddit_producer.py


def push_custom_post(content: str, keyword: str = "manual", engagement: int = 0):
    """
    Push a custom message to tweet_queue with the same JSON payload structure
    as reddit_producer.py:
        payload = [post_id, content, post_time, retry_count, engagement]
    """
    post_id = f"custom_{uuid.uuid4().hex[:10]}"
    post_time = time.time()
    retry_count = 0

    dedup_key = f"post:{post_id}"
    if r.exists(dedup_key):
        logger.warning(f"Duplicate post_id {post_id} — skipping.")
        return None

    r.set(dedup_key, 1, ex=DEDUP_TTL)

    # Identical structure to reddit_producer.py
    payload = [post_id, content, post_time, retry_count, engagement]

    try:
        r.lpush("tweet_queue", json.dumps(payload))
        logger.info(
            f"[CUSTOM PRODUCER] Pushed to queue: {post_id} "
            f"| keyword='{keyword}' | engagement={engagement} "
            f"| content='{content[:80]}{'...' if len(content) > 80 else ''}'"
        )
        return post_id
    except redis.RedisError as e:
        logger.error(f"Redis push failed: {e}")
        return None


def interactive_mode():
    """
    Interactive loop — type messages directly in the terminal.
    """
    print("\n=== Custom Producer — Interactive Mode ===")
    print("Type your message and press Enter to push it to tweet_queue.")
    print("Commands:  :quit — exit  |  :peek — show last 5 queue items\n")

    while True:
        try:
            raw = input("Message > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue

        if raw == ":quit":
            print("Bye!")
            break

        if raw == ":peek":
            items = r.lrange("tweet_queue", 0, 4)
            if not items:
                print("  [Queue is empty]")
            for i, item in enumerate(items):
                try:
                    parsed = json.loads(item)
                    post_id, content, ts, retries, eng = parsed
                    print(f"  [{i}] id={post_id} | eng={eng} | content='{str(content)[:60]}...'")
                except Exception:
                    print(f"  [{i}] (unparseable) {item}")
            continue

        # Optional inline metadata: "My message | keyword=test engagement=42"
        keyword = "manual"
        engagement = 0
        message = raw

        if "|" in raw:
            parts = raw.split("|")
            message = parts[0].strip()
            for part in parts[1:]:
                part = part.strip()
                if part.startswith("keyword="):
                    keyword = part.split("=", 1)[1].strip()
                elif part.startswith("engagement="):
                    try:
                        engagement = int(part.split("=", 1)[1].strip())
                    except ValueError:
                        pass

        push_custom_post(message, keyword=keyword, engagement=engagement)


def batch_mode(messages: list[str], keyword: str = "manual", engagement: int = 0):
    """
    Push a list of messages in one go (useful for scripting).
    """
    logger.info(f"Batch mode: pushing {len(messages)} message(s)...")
    for msg in messages:
        push_custom_post(msg, keyword=keyword, engagement=engagement)
        time.sleep(0.2)  # small delay to avoid flooding


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Custom producer — push test messages to tweet_queue with the same "
                    "payload structure as reddit_producer.py"
    )
    parser.add_argument(
        "messages",
        nargs="*",
        help="One or more messages to push directly (batch mode). "
             "Omit to enter interactive mode.",
    )
    parser.add_argument(
        "--keyword", "-k",
        default="manual",
        help="Keyword tag for the message(s) (default: manual)",
    )
    parser.add_argument(
        "--engagement", "-e",
        type=int,
        default=0,
        help="Fake engagement score (ups + comments) to attach (default: 0)",
    )
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)",
    )

    args = parser.parse_args()

    # Allow overriding Redis connection via CLI flags
    r = redis.Redis(host=args.redis_host, port=args.redis_port, db=0)
    try:
        r.ping()
        logger.info(f"Connected to Redis at {args.redis_host}:{args.redis_port}")
    except redis.ConnectionError as e:
        logger.error(f"Cannot connect to Redis: {e}")
        exit(1)

    if args.messages:
        batch_mode(args.messages, keyword=args.keyword, engagement=args.engagement)
    else:
        interactive_mode()