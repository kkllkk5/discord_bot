from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    title: str # タイトル
    url: str # 記事URL
    source: str # 情報源（例: "GitHub Blog"）
    published_at: datetime # 公開日時
    summary: str # 要約（RSSのsummaryフィールドなどから）