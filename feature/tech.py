import requests
from datetime import datetime, timezone

def parse_iso8601(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S+09:00").replace(tzinfo=timezone.utc)

# -----------------------
# 設定
# -----------------------
MAX_PAGES = 3
ITEMS_PER_PAGE = 100
MIN_LIKES = 5
TOP_N = 5

# -----------------------
# Qiita APIから記事取得
# -----------------------
url = "https://qiita.com/api/v2/items"

all_items = []

for page in range(1, MAX_PAGES + 1):
    params = {
        "per_page": ITEMS_PER_PAGE,
        "page": page
    }

    res = requests.get("https://qiita.com/api/v2/items", params=params)
    items = res.json()

    all_items.extend(items)

print(f"取得件数: {len(all_items)}")

# -----------------------
# スコア計算関数（急上昇）
# -----------------------
def calc_score(item):
    likes = item["likes_count"]
    stocks = item["stocks_count"]

    created = parse_iso8601(item["created_at"])
    hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600

    # 急上昇スコア
    score = (likes + 2 * stocks) / (hours + 2)

    return score, hours

# -----------------------
# フィルタ & スコアリング
# -----------------------
scored = []

for item in items:
    score, hours = calc_score(item)

    # 条件（急上昇らしくする）
    if hours <= 24*3 and item["likes_count"] >= MIN_LIKES:
        scored.append((score, item))

# -----------------------
# ソート
# -----------------------
scored.sort(reverse=True, key=lambda x: x[0])

# -----------------------
# 上位N件出力
# -----------------------
top_items = scored[:TOP_N]

print("🔥 今日の急上昇Qiita記事\n")

for i, (score, item) in enumerate(top_items, 1):
    print(f"{i}. {item['title']}")
    print(f"   👍 {item['likes_count']} / 📌 {item['stocks_count']}")
    print(f"   🔗 {item['url']}")
    print()