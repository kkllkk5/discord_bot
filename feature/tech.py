import requests
from datetime import datetime, timezone

def parse_iso8601(dt_str):
    # ISO 8601 をパースして UTC に変換して返す（Qiita の +09:00 などを正しく扱う）
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)

# -----------------------
# 設定
# -----------------------
# 処理対象となる記事数(ページ数*ページごとのitem数)
MAX_PAGES = 3
ITEMS_PER_PAGE = 100
# 集計対象とする最小いいね数
MIN_LIKES = 5
# 上位N件を出力
TOP_N = 3


def fetch_trending_qiita():
    """
    引数なしで呼べるメイン関数。
    上位 TOP_N 件を出力し、(score, item) タプルのリストを返す。
    """
    url = "https://qiita.com/api/v2/items"
    all_items = []

    for page in range(1, MAX_PAGES + 1):
        params = {
            "per_page": ITEMS_PER_PAGE,
            "page": page
        }

        res = requests.get(url, params=params)
        res.raise_for_status()
        items = res.json()
        all_items.extend(items)

    print(f"取得件数: {len(all_items)}")

    # スコア計算関数（急上昇）
    def calc_score(item):
        likes = item.get("likes_count", 0)
        stocks = item.get("stocks_count", 0)

        created = parse_iso8601(item["created_at"])
        hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600

        # 急上昇スコア
        score = (likes + 2 * stocks) / (hours + 2)

        return score, hours

    # フィルタ & スコアリング
    scored = []

    for item in all_items:
        score, hours = calc_score(item)

        # 条件（急上昇らしくする）
        if hours <= 24 * 2 and item.get("likes_count", 0) >= MIN_LIKES:
            scored.append((score, item))

    # ソート
    scored.sort(reverse=True, key=lambda x: x[0])

    # 上位N件出力
    top_items = scored[:TOP_N]

    message = "🔥急上昇Qiita記事をお知らせします\n"

    for i, (score, item) in enumerate(top_items, 1):
        message += f"{i}. {item['title']}\n"
        message += f"   👍 {item['likes_count']} / 📌 {item['stocks_count']}\n"
        message += f"   🔗 {item['url']}\n\n"

    return message


# -----------------------
# 実行
# -----------------------
if __name__ == "__main__":
    fetch_trending_qiita()