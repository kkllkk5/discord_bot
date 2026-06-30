import os
from google import genai
from google.genai import types
import json
import feedparser
import sys
import datetime
from feature.models.article import Article
from feature.models.hacker_article import HackerArticle
from dateutil import parser
import requests


client = None
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema={
        "type": "OBJECT",
        "properties": {
            "summary": {"type": "STRING"}
        },
        "required": ["summary"]
    }
)


def get_client():
    global client
    if client is None:
        api_key = os.getenv("GENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("GENAI_API_KEY environment variable is not set")
        client = genai.Client(api_key=api_key)
    return client


# RSS指定先のURL
RSS_FEEDS = {
    "GitHub Blog": "https://github.blog/feed/",
    "Cloudflare Blog": "https://blog.cloudflare.com/rss/",
    "OpenAI News": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default?alt=rss",
    "Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",
    #"Hacker News RSS": "https://news.ycombinator.com/rss",
    #"Reddit": "https://www.reddit.com/r/programming/.rss",

}

MIN_LIKES = 5
MIN_COMMENTS = 3


HACKER_NEWS_BASE_URL = "https://hacker-news.firebaseio.com/v0"

# Hacker Newsの新着記事をlimitの件数取得する関数
def get_new_hacker_news_articles(limit=100) -> list[HackerArticle]:
    try:
        # 公式APIから取得
        response = requests.get(f"{HACKER_NEWS_BASE_URL}/newstories.json")
        response.raise_for_status()
        story_ids = response.json()[:limit]
        articles = []

        # IDリストから各記事の詳細を取得
        for story_id in story_ids:
            story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            story_response.raise_for_status()
            story_data = story_response.json()

            if ('title' in story_data) and ('url' in story_data) and ('time' in story_data):
                articles.append(HackerArticle(
                    title=story_data['title'],
                    score=story_data.get('score', 0),
                    descendants=story_data.get('descendants', 0),
                ))

        return articles
    except Exception as e:
        print(f"Error fetching Hacker News articles: {e}")
        return []

def is_interested(article: HackerArticle) -> bool:
    # スコアが5以上、またはコメント数が3以上の記事を興味深いと判断
    return article.score >= MIN_LIKES or article.descendants >= MIN_COMMENTS

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

# 最近の記事のみをフィルタリングする関数（24時間以内を想定）
def filter_recent_articles(articles: list[Article], hours: int=24) -> list[Article]:
    now = datetime.datetime.now(datetime.timezone.utc)

    # 記事のフィルタリング用関数
    def is_recent_article(article: Article) -> bool:
        return (now - article.published_at).total_seconds() < (hours * 3600)

    recent_articles = list(filter(is_recent_article, articles))
    return recent_articles


# 記事の要約を生成する関数（gemini APIにより自動で要約,日本語へと翻訳）
# 現状は記事データの要約をそのまま使用，日本語化のみ投げる
def summarize_article(article: Article) -> str:
    response_json = get_client().models.generate_content(
        model="gemini-3.5-flash",
        config=config,
        contents="以下の記事の要約を日本語化してください: " + article.summary
    )
    
    response = json.loads(response_json.text)

    return f"{article.title} - {response['summary']}"


if __name__ == "__main__":
    main()

def main():
    """
    response = "技術ニュースをお知らせします!\n"
    count = 1
    for source_name, url in RSS_FEEDS.items():
        articles = fetch_rss_feed(source_name, url)
        #print(f"Fetched {len(articles)} articles from {source_name}")
        recent_articles = filter_recent_articles(articles)
        for article in recent_articles:
            response += f"{count}. {summarize_article(article)}\n"
            count += 1

    return response
    """
    # Hacker Newsの新着記事を取得
    hacker_articles = get_new_hacker_news_articles()
    # 興味深い記事のみをフィルタリング
    interested_articles = [article for article in hacker_articles if is_interested(article)]
    
    response = ""
    # 結果を表示
    if interested_articles:
        response += "興味深いHacker Newsの記事:\n"
        for article in interested_articles:
            response += f"タイトル: {article.title}, スコア: {article.score}, コメント数: {article.descendants}\n"
    else:
        response += "興味深いHacker Newsの記事は見つかりませんでした。"
    return response
