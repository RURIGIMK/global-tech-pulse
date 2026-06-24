import httpx
import os
import json
import asyncio
import hashlib
import base64
from config import NEWSAPI_KEY

CATEGORY_MAP = {
    "Artificial Intelligence": [
        "ai", "machine learning", "gpt", "llm", "neural network",
        "deep learning", "openai", "chatgpt", "copilot", "gemini"
    ],
    "Startups & Business": [
        "startup", "funding", "ipo", "venture capital", "acquire", "valuation"
    ],
    "Gadgets & Hardware": [
        "smartphone", "laptop", "gpu", "chip", "apple", "samsung", "wearable", "device"
    ],
    "Cybersecurity": [
        "cyber", "hack", "vulnerability", "ransomware", "data breach", "malware"
    ],
    "Software & Programming": [
        "javascript", "python", "api", "framework", "open source", "github", "devops"
    ],
    "Science & Emerging Tech": [
        "quantum", "biotech", "space", "nuclear", "fusion", "nanotech", "robotics"
    ]
}

NON_TECH_KEYWORDS = [
    "politics", "election", "sport", "celebrity", "weather", "recipe", "fashion"
]

def is_tech_article(article: dict) -> bool:
    text = (article.get("title", "") + " " + article.get("description", "")).lower()
    return not any(word in text for word in NON_TECH_KEYWORDS)

def assign_category(article: dict) -> str:
    text = (
        article.get("title", "") + " "
        + article.get("description", "") + " "
        + (article.get("content", "") or "")
    ).lower()
    for category, keywords in CATEGORY_MAP.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other Tech"

def _hash_url(url: str) -> str:
    return base64.urlsafe_b64encode(
        hashlib.sha256(url.encode()).digest()[:8]
    ).decode().rstrip("=")

async def fetch_and_process_news() -> list[dict]:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "technology",
        "language": "en",
        "pageSize": 100,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY,
    }
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "ok":
        raise Exception(f"NewsAPI error: {data.get('message', 'unknown error')}")

    articles = data.get("articles", [])
    # Keep only articles with mandatory fields
    articles = [
        a for a in articles
        if a.get("title") and a.get("url") and a.get("urlToImage") and a.get("publishedAt")
    ]
    # Tech filter
    articles = [a for a in articles if is_tech_article(a)]

    # Deduplicate by url
    seen = set()
    deduped = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            deduped.append(a)
    articles = deduped

    processed = []
    for article in articles:
        if len(processed) >= 50:
            break
        category = assign_category(article)
        if category == "Other Tech" and len(processed) > 30:
            continue

        processed.append({
            "id": _hash_url(article["url"]),
            "title": article["title"],
            "description": article.get("description", ""),
            "url": article["url"],
            "image": article["urlToImage"],
            "source": article.get("source", {}).get("name", "Unknown"),
            "publishedAt": article["publishedAt"],
            "category": category,
            "summary": article.get("description", ""),
        })
        print(f"Processed: {article['title'][:60]}")

    print(f"Final processed count: {len(processed)}")
    return processed

async def main():
    articles = await fetch_and_process_news()
    # Write to frontend/public/data/articles.json
    out_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "articles.json")
    with open(out_path, "w") as f:
        json.dump(articles, f, indent=2)
    print(f"Saved {len(articles)} articles to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())