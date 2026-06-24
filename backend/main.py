from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
from news_service import fetch_and_process_news
from kv_store import kv

app = FastAPI()

# ---------- API Routes ----------
@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.api_route("/api/refresh-news", methods=["GET", "POST"])
async def refresh_news():
    articles = await fetch_and_process_news()
    await kv.set("articles", articles)
    for article in articles:
        await kv.set(f"article:{article['id']}", article)
    return {"success": True, "count": len(articles)}

@app.get("/api/articles")
async def get_articles():
    articles = await kv.get("articles")
    if articles is None:
        articles = await fetch_and_process_news()
        await kv.set("articles", articles)
    return articles

@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    article = await kv.get(f"article:{article_id}")
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

# ---------- Serve the React Frontend ----------
# Production (Vercel): the build step copies frontend/dist → backend/static
# Local dev: we serve from ../frontend/dist
static_dir = os.path.join(os.path.dirname(__file__), "static")
dev_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(static_dir) and os.path.isfile(os.path.join(static_dir, "index.html")):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
elif os.path.exists(dev_dir) and os.path.isfile(os.path.join(dev_dir, "index.html")):
    app.mount("/", StaticFiles(directory=dev_dir, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {"error": "Frontend not built. Run 'npm run build' inside frontend/"}