from dataclasses import dataclass
from datetime import datetime


@dataclass
class HackerArticle:
    title: str # タイトル
    score: int # スコア（いいね数）
    descendants: int # コメント数