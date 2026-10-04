import asyncio
import os
import sys
import threading
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from server import app
from dashboard.runtime import RuntimeBridge
from dashboard.store import Store
from dashboard.web import get_store

TOKEN = 'test-admin-token-' + 'x' * 32
ORIGIN = 'http://testserver'

class FakeClient:
    activity = None
    latency = .042
    guilds = [object(), object()]
    ready = True
    def __init__(self):
        self.presence_calls = []
    def is_ready(self):
        return self.ready
    async def change_presence(self, **kwargs):
        self.presence_calls.append(kwargs)

@pytest.fixture
def env(tmp_path, monkeypatch):
    path = tmp_path/'dashboard.sqlite3'
    monkeypatch.setenv('DASHBOARD_DB_PATH', str(path))
    monkeypatch.setenv('DASHBOARD_TOKEN', TOKEN)
    monkeypatch.setenv('DASHBOARD_ORIGIN', ORIGIN)
    store = Store(path)
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client, store
    app.dependency_overrides.clear()


def login(client):
    response = client.post('/api/dashboard/session', json={'token': TOKEN}, headers={'Origin': ORIGIN})
    assert response.status_code == 200
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert 'samesite=strict' in response.headers['set-cookie'].lower()


def test_html_and_assets_and_authentication(env):
    client, store = env
    page = client.get('/dashboard')
    assert page.status_code == 200
    assert 'Botダッシュボード' in page.text
    assert 'DemoAdapter' not in page.text
    assert 'start-bot' not in page.text
    assert client.get('/dashboard/assets/app.js').status_code == 200
    assert client.get('/dashboard/assets/store.py').status_code == 404
    assert client.get('/api/dashboard/snapshot').status_code == 401
    assert client.post('/api/dashboard/session', json={'token':'wrong'}, headers={'Origin':ORIGIN}).status_code == 401
    login(client)
    snapshot = client.get('/api/dashboard/snapshot')
    assert snapshot.status_code == 200
    assert snapshot.headers['cache-control'] == 'no-store'
    assert snapshot.json()['controlsEnabled'] is False
    assert snapshot.json()['logs'] == []


def test_token_missing_disables_all_admin_access(env, monkeypatch):
    client, _ = env
    monkeypatch.delenv('DASHBOARD_TOKEN')
    assert client.get('/api/dashboard/snapshot').status_code == 503


def test_csrf_rejected_before_confirmation_or_queue_write(env):
    client, store = env
    login(client)
    runtime = RuntimeBridge(FakeClient(), store)
    runtime.connected = True
    runtime.publish()
    payload = {'action': {'kind':'presence','value':'idle'}}
    assert client.post('/api/dashboard/actions/prepare', json=payload, headers={'Origin':'https://other.test'}).status_code == 403
    assert client.post('/api/dashboard/actions/prepare', json=payload).status_code == 403
    with store.connection() as db:
        assert db.execute('SELECT count(*) FROM confirmations').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM commands').fetchone()[0] == 0


def test_real_bridge_applies_feature_and_presence_only_after_confirmation(env):
    client, store = env
    login(client)
    fake = FakeClient()
    # APIとBotは別のStoreインスタンスで同じファイルを共有する。
    bridge = RuntimeBridge(fake, Store(store.path))
    bridge.connected = True
    bridge.publish()
    stop = threading.Event()
    def consume():
        while not stop.wait(.02):
            asyncio.run(bridge.poll())
    thread = threading.Thread(target=consume)
    thread.start()
    try:
        for action in [{'kind':'feature','featureId':'meal_analyze','enabled':False}, {'kind':'presence','value':'idle'}]:
            prepared = client.post('/api/dashboard/actions/prepare', json={'action':action}, headers={'Origin':ORIGIN})
            assert prepared.status_code == 200
            ticket = prepared.json()['id']
            if action['kind'] == 'feature':
                assert bridge.enabled('meal_analyze') is True
            else:
                assert fake.presence_calls == []
            bad = client.post('/api/dashboard/actions/execute', json={'ticketId':ticket,'action':action,'confirmed':False}, headers={'Origin':ORIGIN})
            assert bad.status_code == 409
            result = client.post('/api/dashboard/actions/execute', json={'ticketId':ticket,'action':action,'confirmed':True}, headers={'Origin':ORIGIN})
            assert result.status_code == 200
            replay = client.post('/api/dashboard/actions/execute', json={'ticketId':ticket,'action':action,'confirmed':True}, headers={'Origin':ORIGIN})
            assert replay.status_code == 409
        assert bridge.enabled('meal_analyze') is False
        assert str(fake.presence_calls[0]['status']) == 'idle'
        data = client.get('/api/dashboard/snapshot').json()
        assert data['bot']['latencyMs'] == 42
        assert data['bot']['guilds'] == 2
        assert data['bot']['presence'] == 'idle'
        assert all(a['result']=='成功' for a in data['audit'])
    finally:
        stop.set()
        thread.join(timeout=2)


def test_unsupported_process_controls_are_rejected(env):
    client, store = env
    login(client)
    runtime = RuntimeBridge(FakeClient(),store)
    runtime.connected = True
    runtime.publish()
    for kind in ['start','stop','restart','shell']:
        response = client.post('/api/dashboard/actions/prepare', json={'action':{'kind':kind}}, headers={'Origin':ORIGIN})
        assert response.status_code == 409


def test_logout_revokes_cookie_and_unexecuted_confirmation(env):
    client, store = env
    login(client)
    runtime = RuntimeBridge(FakeClient(),store)
    runtime.connected = True
    runtime.publish()
    prepared = client.post('/api/dashboard/actions/prepare', json={'action':{'kind':'presence','value':'dnd'}}, headers={'Origin':ORIGIN})
    assert prepared.status_code == 200
    old_cookie = client.cookies.get('dashboard_session')
    assert client.post('/api/dashboard/logout', json={}, headers={'Origin':ORIGIN}).status_code == 200
    assert store.session_actor(old_cookie,TOKEN) is None
    assert client.get('/api/dashboard/snapshot').status_code == 401
    with store.connection() as db:
        assert db.execute('SELECT count(*) FROM confirmations').fetchone()[0] == 0
