import os
from google import genai
from google.genai import types
import json
import feedparser
import sys
import datetime
from models.article import Article
from dateutil import parser

"""
client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
config = types.GenerateContentConfig(
    max_output_tokens=20,
    temperature=0.2,
    thinking_config={"thinking_budget": 0},
    response_schema={
        "type": "OBJECT",
        "properties": {
            "move": {"type": "STRING"}
        },
        "required": ["move"]
    }
)
"""

# RSS指定先のURL
RSS_FEEDS = {
    "GitHub Blog": "https://github.blog/feed/",
    "Cloudflare Blog": "https://blog.cloudflare.com/rss/",
    "OpenAI News": "https://openai.com/news/rss.xml",
    #"Google AI Blog": "https://ai.googleblog.com/feeds/posts/default?alt=rss",
    #"Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",
    "Hacker News RSS": "https://news.ycombinator.com/rss",
    #"Reddit": "https://www.reddit.com/r/programming/.rss",

}


# RSSフィードから記事を全件取得する関数
def fetch_rss_feed(source_name:str,url:str) -> list[Article]:
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        try:
            published = parser.parse(entry.published)
        except Exception:
            print(f"Error parsing date for entry: {entry.title}")
            continue

        summary = getattr(entry, "summary", "")
        articles.append(
            Article(
                title=entry.title,
                url=entry.link,
                source=source_name,
                published_at=parser.parse(entry.published),
                summary=getattr(entry, "summary", ""),
            )
        )

    return articles

# 最近の記事のみをフィルタリングする関数（72時間以内を想定）
def filter_recent_articles(articles: list[Article], hours: int=72) -> list[Article]:
    now = datetime.datetime.now(datetime.timezone.utc)

    # 記事のフィルタリング用関数
    def is_recent_article(article: Article) -> bool:
        return (now - article.published_at).total_seconds() < (hours * 3600)

    recent_articles = list(filter(is_recent_article, articles))
    return recent_articles


if __name__ == "__main__":
    for source_name, url in RSS_FEEDS.items():
        articles = fetch_rss_feed(source_name, url)
        print(f"Fetched {len(articles)} articles from {source_name}")
        recent_articles = filter_recent_articles(articles)
        for article in recent_articles:
            print(f"- {article.title} ({article.published_at.isoformat()})")
