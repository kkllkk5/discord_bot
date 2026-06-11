import os
from google import genai
from google.genai import types
import json
import requests
import feedparser

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
}

def fetch_rss_feed(source_name,url):
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append(entry)

    return articles

if __name__ == "__main__":
    for source_name, url in RSS_FEEDS.items():
        articles = fetch_rss_feed(source_name, url)
        print(f"Fetched {len(articles)} articles from {source_name}")



