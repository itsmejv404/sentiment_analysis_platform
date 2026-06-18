import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import config
from backend.db.models import ProductSentiment

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "are",
    "around",
    "ask",
    "be",
    "best",
    "do",
    "does",
    "for",
    "from",
    "get",
    "had",
    "has",
    "have",
    "how",
    "is",
    "it",
    "kind",
    "me",
    "much",
    "of",
    "on",
    "or",
    "show",
    "tell",
    "than",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "top",
    "trend",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
    "people",
    "feel",
    "feeling",
    "say",
    "saying",
    "think",
}


def _json_from_text(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return {}


def _normalize_terms(terms: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for term in terms:
        cleaned = re.sub(r"\s+", " ", str(term).strip().lower())
        if not cleaned or len(cleaned) < 2 or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized[:8]


def _fallback_keywords(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", query.lower())
    return _normalize_terms([token for token in tokens if token not in STOPWORDS])


def extract_keywords(query: str, tenant_keywords: list[str] | None = None) -> dict:
    tenant_keywords = _normalize_terms(tenant_keywords or [])
    fallback_terms = _fallback_keywords(query)

    if not config.GROQ_API_KEY:
        return {
            "keywords": fallback_terms or tenant_keywords,
            "focus": fallback_terms[0] if fallback_terms else (tenant_keywords[0] if tenant_keywords else query),
            "summary_hint": "",
        }

    prompt = f"""
Extract the main search keywords from this user question.
Return JSON only with this shape:
{{"keywords": ["battery"], "focus": "battery", "summary_hint": "short note"}}

Question: {query}
Known organization keywords: {tenant_keywords}

Rules:
- Return 1 to 5 concise search terms.
- Prefer product or topic nouns.
- Include useful multi-word phrases when they matter.
- Do not add markdown or extra text.
""".strip()

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You extract concise search keywords for sentiment analysis queries."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = _json_from_text(content)
    except Exception:
        parsed = {}

    keywords = _normalize_terms(parsed.get("keywords") or [])
    if not keywords:
        keywords = fallback_terms or tenant_keywords

    focus = str(parsed.get("focus") or (keywords[0] if keywords else query)).strip()
    summary_hint = str(parsed.get("summary_hint") or "").strip()

    return {
        "keywords": keywords,
        "focus": focus,
        "summary_hint": summary_hint,
    }


def _build_filter_clauses(keywords: list[str]):
    clauses = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        clauses.extend([
            ProductSentiment.product.ilike(pattern),
            ProductSentiment.content.ilike(pattern),
            ProductSentiment.keywords.ilike(pattern),
        ])
    return clauses


def fetch_sentiment_matches(
    db: Session,
    tenant_id: int,
    keywords: list[str],
    timeframe: str | None = None,
):
    query = db.query(ProductSentiment).filter(ProductSentiment.tenant_id == tenant_id)

    now = datetime.now(timezone.utc)
    if timeframe == "1h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=1))
    elif timeframe == "12h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=12))
    elif timeframe == "24h":
        query = query.filter(ProductSentiment.post_createdat >= now - timedelta(hours=24))

    if keywords:
        clauses = _build_filter_clauses(keywords)
        if clauses:
            query = query.filter(or_(*clauses))

    rows = query.order_by(ProductSentiment.post_createdat.desc()).limit(200).all()
    return rows


def summarize_matches(rows, query: str, focus: str, keywords: list[str], summary_hint: str = "") -> dict:
    total = len(rows)
    positive = sum(1 for row in rows if row.sentiment == "POSITIVE")
    negative = sum(1 for row in rows if row.sentiment == "NEGATIVE")
    neutral = sum(1 for row in rows if row.sentiment == "NEUTRAL")
    mixed = total - positive - negative - neutral

    avg_score = round(sum(float(row.overall_score or 0) for row in rows) / total, 3) if total else 0.0
    product_counts = Counter((row.product or "Unknown").strip() for row in rows)
    sample_posts = [
        {
            "id": row.id,
            "content": (row.content or "")[:220],
            "sentiment": row.sentiment,
            "product": row.product,
            "score": row.overall_score,
            "timestamp": row.post_createdat.isoformat() if row.post_createdat else None,
        }
        for row in rows[:5]
    ]

    chart_data = [
        {"t": row.post_createdat.isoformat(), "s": row.sentiment}
        for row in rows
        if row.post_createdat
    ]

    visual_summary = {
        "type": "doughnut",
        "labels": ["Positive", "Negative", "Neutral"],
        "values": [positive, negative, neutral],
    }

    if config.GROQ_API_KEY and total:
        summary_prompt = f"""
You are summarizing a tenant's sentiment query result.
Write 2 short sentences max.
Be concrete, concise, and friendly.
Mention the main keyword focus, the dominant sentiment, and one practical takeaway.
Do not use markdown.

User query: {query}
Focus: {focus}
Matched keywords: {keywords}
Summary hint: {summary_hint}
Counts: positive={positive}, negative={negative}, neutral={neutral}, mixed={mixed}, total={total}
Average score: {avg_score}
Top products: {product_counts.most_common(3)}
Example posts: {sample_posts}
""".strip()

        try:
            response = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {config.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "You turn sentiment analysis results into concise business insights."},
                        {"role": "user", "content": summary_prompt},
                    ],
                    "temperature": 0.2,
                },
                timeout=20,
            )
            response.raise_for_status()
            summary_text = response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            summary_text = ""
    else:
        summary_text = ""

    if not summary_text:
        dominant = "positive" if positive >= negative and positive >= neutral else "negative" if negative >= positive and negative >= neutral else "neutral"
        summary_text = (
            f"I found {total} matching mentions about {focus or 'the topic'}. "
            f"Sentiment is mostly {dominant} with {positive} positive, {negative} negative, and {neutral} neutral mentions."
        )

    return {
        "summary_text": summary_text,
        "visual_summary": visual_summary,
        "summary": {
            "total_mentions": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "mixed": mixed,
            "positive_pct": round((positive / total * 100), 1) if total else 0,
            "negative_pct": round((negative / total * 100), 1) if total else 0,
            "neutral_pct": round((neutral / total * 100), 1) if total else 0,
        },
        "chart_data": chart_data,
        "sample_posts": sample_posts,
        "top_products": [
            {"product": product, "mentions": count}
            for product, count in product_counts.most_common(5)
        ],
        "average_score": avg_score,
    }