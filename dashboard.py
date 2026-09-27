"""Read-only prototype dashboard for the Discord bot.

This module intentionally has no dependency on the running Discord client.  It
can therefore be served alongside the bot without changing its lifecycle.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["dashboard"])

FEATURES = [
    {"name": "食事画像のAI解析", "description": "Geminiで食事画像の内容を解析します。", "category": "AI"},
    {"name": "S乱リザルト解析", "description": "IIDXリザルトを解析しNotionを更新します。", "category": "IIDX"},
    {"name": "IIDX課題曲生成", "description": "レベル11・12から課題曲をランダムに選びます。", "category": "IIDX"},
    {"name": "DP非公式難易度検索", "description": "曲名からDP非公式難易度を検索します。", "category": "IIDX"},
    {"name": "技術トレンド通知", "description": "Qiitaの急上昇記事を定期的に通知します。", "category": "通知"},
]


def overview() -> dict[str, Any]:
    return {
        "service": "Dashboard API",
        "service_status": "online",
        "bot_status": "not_connected",
        "feature_count": len(FEATURES),
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def bot_status() -> dict[str, str]:
    return {
        "status": "not_connected",
        "label": "未連携",
        "detail": "このプロトタイプはDiscordクライアントの実行状態をまだ監視していません。",
    }


def logs() -> list[dict[str, str]]:
    return [
        {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": "INFO",
            "message": "Dashboard prototype is running. Runtime logs are not connected yet.",
        }
    ]


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page() -> str:
    return DASHBOARD_HTML


@router.get("/api/dashboard/overview")
def get_overview() -> dict[str, Any]:
    return overview()


@router.get("/api/dashboard/bot-status")
def get_bot_status() -> dict[str, str]:
    return bot_status()


@router.get("/api/dashboard/features")
def get_features() -> list[dict[str, str]]:
    return FEATURES


@router.get("/api/dashboard/logs")
def get_logs() -> list[dict[str, str]]:
    return logs()


DASHBOARD_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Discord Bot Dashboard</title>
  <style>
    :root { color-scheme: dark; --bg:#10131a; --surface:#1a1f2b; --line:#30394b; --text:#edf1f7; --muted:#a8b2c3; --accent:#6da8ff; --ok:#4ad295; --warn:#f0b35d; }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:15px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    header { padding:28px max(24px,calc((100vw - 1120px)/2)); border-bottom:1px solid var(--line); background:#151a24; }
    h1 { margin:0; font-size:25px; } header p { color:var(--muted); margin:5px 0 0; }
    main { max-width:1120px; margin:auto; padding:28px 24px 52px; } h2 { font-size:18px; margin:32px 0 12px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; } .card { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:18px; }
    .label { color:var(--muted); font-size:13px; } .value { font-size:23px; font-weight:700; margin-top:7px; } .status { color:var(--warn); }
    .features { display:grid; grid-template-columns:repeat(auto-fit,minmax(245px,1fr)); gap:12px; } .feature h3 { margin:0; font-size:16px; } .feature p { color:var(--muted); margin:7px 0; } .tag { color:var(--accent); font-size:12px; }
    .logs { background:#0c0f15; border:1px solid var(--line); border-radius:12px; padding:12px 16px; font:13px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace; color:#c8d1df; white-space:pre-wrap; }
    .note { color:var(--muted); } @media (max-width:560px) { header { padding:22px 18px; } main { padding:22px 18px; } }
  </style>
</head>
<body>
  <header><h1>Discord Bot Dashboard</h1><p>読み取り専用プロトタイプ · 認証・操作機能なし</p></header>
  <main>
    <h2>Overview</h2><section class="grid" id="overview"><div class="card">読み込み中…</div></section>
    <h2>Bot status</h2><section class="card"><div class="value status" id="bot-status">読み込み中…</div><p class="note" id="bot-detail"></p></section>
    <h2>Features</h2><section class="features" id="features"></section>
    <h2>Logs</h2><section class="logs" id="logs">読み込み中…</section>
  </main>
  <script>
    const get = async (path) => (await fetch(path)).json();
    const esc = (value) => String(value).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    Promise.all([get('/api/dashboard/overview'), get('/api/dashboard/bot-status'), get('/api/dashboard/features'), get('/api/dashboard/logs')]).then(([overview, status, features, logs]) => {
      document.querySelector('#overview').innerHTML = [
        ['Dashboard API', overview.service_status], ['Bot', overview.bot_status], ['Features', overview.feature_count]
      ].map(([label,value]) => `<div class="card"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`).join('');
      document.querySelector('#bot-status').textContent = status.label;
      document.querySelector('#bot-detail').textContent = status.detail;
      document.querySelector('#features').innerHTML = features.map(feature => `<article class="card feature"><h3>${esc(feature.name)}</h3><p>${esc(feature.description)}</p><span class="tag">${esc(feature.category)}</span></article>`).join('');
      document.querySelector('#logs').textContent = logs.map(log => `[${log.timestamp}] ${log.level}  ${log.message}`).join('\n');
    }).catch(() => { document.querySelector('#overview').textContent = 'Dashboard APIを取得できませんでした。'; });
  </script>
</body>
</html>"""
