"""Dashboard HTML/assets and session-authenticated, confirmation-gated API."""
import asyncio
import os
from pathlib import Path
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from .store import Store

router = APIRouter(tags=["dashboard"])
ROOT = Path(__file__).resolve().parent
COOKIE = "dashboard_session"

# 呼び出しごとに共有DBを開く。テストと両プロセスはDASHBOARD_DB_PATHで保存先を指定できる。
def get_store():
    return Store()

# POSTが同じオリジンからのJSONであることを検証する。構成済みOriginがあればそれを優先する。
def require_origin(request: Request):
    expected = os.getenv("DASHBOARD_ORIGIN", str(request.base_url).rstrip("/")).rstrip("/")
    if request.headers.get("origin") != expected:
        raise HTTPException(403, "同じオリジンからの操作だけが許可されています")
    if request.headers.get("content-type", "").split(";",1)[0].strip() != "application/json":
        raise HTTPException(415, "JSON形式が必要です")

# セッションの期限と管理者トークンを検証する。トークン未設定時は全管理APIを無効にする。
def require_admin(request: Request, store: Store = Depends(get_store)):
    token = os.getenv("DASHBOARD_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(503, "DASHBOARD_TOKENに32文字以上の管理用トークンを設定してください")
    actor = store.session_actor(request.cookies.get(COOKIE), token)
    if not actor:
        raise HTTPException(401, "管理者ログインが必要です")
    return actor

# JSONオブジェクトを読む。不正・余分なフィールドはハンドラー側も検証する。
async def read_json(request):
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(400, "JSONが不正です")
    if not isinstance(data, dict):
        raise HTTPException(400, "JSONオブジェクトが必要です")
    return data

# 相対アセットの基点を揃えるため、末尾スラッシュ付きURLへ誘導する。
@router.get("/dashboard", include_in_schema=False)
def dashboard_redirect():
    return RedirectResponse("/dashboard/", status_code=307)

# シークレットを含まない画面を配信する。状態・ログ取得には別途ログインが必要。
@router.get("/dashboard/", include_in_schema=False)
def dashboard_page():
    return FileResponse(ROOT/"index.html", headers={"Cache-Control":"no-store"})

# 既知の静的アセットだけ配信し、DB・Pythonソースへのパストラバーサルを拒否する。
@router.get("/dashboard/assets/{filename}", include_in_schema=False)
def dashboard_asset(filename: str):
    if filename not in {"app.js","adapter.js","controller.js","style.css","favicon.svg"}:
        raise HTTPException(404)
    return FileResponse(ROOT/"assets"/filename, headers={"Cache-Control":"no-cache"})

# 管理用トークンを定時間比較し、HttpOnly/SameSite cookieを発行する。ブラウザにはトークンを保存しない。
@router.post("/api/dashboard/session", dependencies=[Depends(require_origin)])
async def login(request: Request, response: Response, store: Store = Depends(get_store)):
    configured = os.getenv("DASHBOARD_TOKEN", "")
    if len(configured) < 32:
        raise HTTPException(503, "DASHBOARD_TOKENに32文字以上の管理用トークンを設定してください")
    data = await read_json(request)
    value = data.get("token")
    if set(data) != {"token"} or not isinstance(value, str) or not secrets.compare_digest(value.encode(), configured.encode()):
        raise HTTPException(401, "管理用トークンが違います")
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(COOKIE, store.new_session(configured), max_age=28800, httponly=True, secure=request.url.scheme=="https", samesite="strict", path="/")
    return {"ok":True}

# セッションと確認券を失効させる。Bot状態には影響しない。
@router.post("/api/dashboard/logout", dependencies=[Depends(require_origin)])
def logout(response: Response, actor: str = Depends(require_admin), store: Store = Depends(get_store)):
    store.logout(actor)
    response.delete_cookie(COOKIE, path="/")
    return {"ok":True}

# 認証済み管理者に実Botの状態・設定・ログ・操作履歴を返す。
@router.get("/api/dashboard/snapshot")
def snapshot(response: Response, actor: str = Depends(require_admin), store: Store = Depends(get_store)):
    response.headers["Cache-Control"] = "no-store"
    return store.snapshot()

# 操作対象を確認するための確認券だけを発行する。Botの状態は変更しない。
@router.post("/api/dashboard/actions/prepare", dependencies=[Depends(require_origin)])
async def prepare(request: Request, actor: str = Depends(require_admin), store: Store = Depends(get_store)):
    data = await read_json(request)
    if set(data) != {"action"}:
        raise HTTPException(400, "actionだけを指定してください")
    try:
        return store.prepare(actor, data["action"])
    except ValueError as error:
        raise HTTPException(409, str(error))

# 確認券を1回消費してBotへ操作を渡す。Botの実適用を確認してから成功を返し、自動再試行しない。
@router.post("/api/dashboard/actions/execute", dependencies=[Depends(require_origin)])
async def execute(request: Request, actor: str = Depends(require_admin), store: Store = Depends(get_store)):
    data = await read_json(request)
    if set(data) != {"ticketId","action","confirmed"} or not isinstance(data.get("ticketId"), str):
        raise HTTPException(400, "操作の形式が不正です")
    try:
        command = store.enqueue(actor, data["ticketId"], data["action"], data["confirmed"])
    except ValueError as error:
        raise HTTPException(409, str(error))
    for _ in range(65):
        result = store.command(command)
        if result["state"] == "done":
            return {"ok":True}
        if result["state"] in {"failed","cancelled","unknown"}:
            raise HTTPException(409, result["error"])
        await asyncio.sleep(.1)
    raise HTTPException(504, "Botから結果を確認できませんでした。状態と操作履歴を確認し、再実行前に再確認してください")
