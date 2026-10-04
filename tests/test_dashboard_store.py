import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import pytest
from dashboard.store import Store, validate_action
from dashboard.runtime import DatabaseLogHandler, RuntimeBridge

@pytest.fixture
def store(tmp_path):
    now = [1000.0]
    s = Store(tmp_path/'dashboard.sqlite3', clock=lambda:now[0])
    s.heartbeat('boot-1', {'name':'discord_bot','status':'online','presence':'online','startedAt':'2026-10-04T00:00:00+00:00','latencyMs':42,'guilds':2})
    return s, now


def test_confirmation_is_bound_to_actor_payload_revision_expiry_and_bot(store):
    s, now = store
    action = {'kind':'presence','value':'idle'}
    ticket = s.prepare('admin-1',action)
    with pytest.raises(ValueError):
        s.enqueue('admin-2',ticket['id'],action,True)
    with pytest.raises(ValueError):
        s.enqueue('admin-1',ticket['id'],dict(action,value='dnd'),True)
    with s.connection() as db:
        assert db.execute('SELECT count(*) FROM commands').fetchone()[0] == 0
    s.enqueue('admin-1',ticket['id'],action,True)
    with pytest.raises(ValueError):
        s.enqueue('admin-1',ticket['id'],action,True)
    stale = s.prepare('admin-1',action)
    changed = s.prepare('admin-1',action)
    s.enqueue('admin-1',changed['id'],action,True)
    with pytest.raises(ValueError):
        s.enqueue('admin-1',stale['id'],action,True)
    expired = s.prepare('admin-1',action)
    now[0] += 61
    with pytest.raises(ValueError):
        s.enqueue('admin-1',expired['id'],action,True)


def test_concurrent_api_workers_can_only_consume_a_ticket_once(store):
    s, _ = store
    action = {'kind':'feature','featureId':'iidx','enabled':False}
    ticket = s.prepare('admin', action)
    def enqueue(_):
        try:
            return s.enqueue('admin',ticket['id'],action,True)
        except ValueError:
            return None
    with ThreadPoolExecutor(2) as pool:
        assert sum(bool(result) for result in pool.map(enqueue, range(2))) == 1


def test_stale_bot_and_new_boot_reject_controls(store):
    s, now = store
    action = {'kind':'presence','value':'idle'}
    ticket = s.prepare('admin',action)
    with s.connection() as db:
        db.execute("UPDATE runtime SET boot='boot-2'")
    with pytest.raises(ValueError):
        s.enqueue('admin',ticket['id'],action,True)
    now[0] += 16
    assert s.snapshot()['controlsEnabled'] is False
    assert s.snapshot()['bot']['status'] == 'offline'
    with pytest.raises(ValueError):
        s.prepare('admin',action)


def test_expired_commands_never_run_later(store):
    s, now = store
    action = {'kind':'feature','featureId':'dice','enabled':False}
    t = s.prepare('admin', action)
    command = s.enqueue('admin',t['id'],action,True)
    now[0] += 7
    assert s.command(command)['state'] == 'cancelled'
    assert s.claim('boot-1') is None
    assert s.setting('feature:dice') is True


def test_log_capture_masks_secrets_and_bounds_buffer(store, monkeypatch):
    s, _ = store
    monkeypatch.setenv('TOKEN','SECRET-DISCORD-TOKEN')
    handler = DatabaseLogHandler(s)
    record = logging.LogRecord('discord.client',logging.ERROR,'',0,'token=%s Bearer OTHER-CREDENTIAL',('SECRET-DISCORD-TOKEN',),None)
    handler.emit(record)
    message = s.snapshot()['logs'][0]['message']
    assert 'SECRET-DISCORD-TOKEN' not in message
    assert 'OTHER-CREDENTIAL' not in message
    for i in range(310):
        s.add_log('INFO','system',str(i))
    assert len(s.snapshot()['logs']) == 300


def test_session_expiry_and_token_rotation(store):
    s, now = store
    cookie = s.new_session('a'*32)
    assert s.session_actor(cookie,'a'*32)
    assert s.session_actor(cookie,'b'*32) is None
    now[0] += 28801
    assert s.session_actor(cookie,'a'*32) is None


def test_invalid_payloads_are_rejected():
    for action in [None,{}, {'kind':['presence']}, {'kind':'presence','value':[]}, {'kind':'feature','featureId':[],'enabled':False}, {'kind':'feature','featureId':'iidx','enabled':0}, {'kind':'presence','value':'idle','extra':True}]:
        with pytest.raises(ValueError):
            validate_action(action)


def test_failed_presence_does_not_report_success_or_save_new_preference(store):
    s, _ = store
    class FailingClient:
        activity = 'existing activity'
        latency = float('inf')
        guilds = []
        def is_ready(self):
            return True
        async def change_presence(self, **kwargs):
            assert kwargs['activity'] == self.activity
            raise RuntimeError('websocket unavailable')
    bridge = RuntimeBridge(FailingClient(), s)
    bridge.connected = True
    bridge.publish()
    action = {'kind':'presence','value':'dnd'}
    ticket = s.prepare('admin',action)
    command = s.enqueue('admin',ticket['id'],action,True)
    asyncio.run(bridge.poll())
    assert s.command(command)['state'] == 'failed'
    assert s.setting('presence') == 'online'
    assert s.snapshot()['audit'][0]['result'] == '失敗'
    assert s.snapshot()['bot']['latencyMs'] is None


def test_disconnected_cache_ready_bot_cannot_apply_commands(store):
    s, _ = store
    class CachedClient:
        activity = None
        latency = .042
        guilds = []
        calls = []
        def is_ready(self):
            return True
        async def change_presence(self, **kwargs):
            self.calls.append(kwargs)
    fake = CachedClient()
    bridge = RuntimeBridge(fake,s)
    bridge.connected = True
    bridge.publish()
    action = {'kind':'presence','value':'idle'}
    ticket = s.prepare('admin',action)
    command = s.enqueue('admin',ticket['id'],action,True)
    bridge.connected = False
    asyncio.run(bridge.poll())
    assert s.snapshot()['bot']['status'] == 'offline'
    assert s.snapshot()['controlsEnabled'] is False
    assert s.command(command)['state'] == 'failed'
    assert not fake.calls


def test_restarted_bot_does_not_replay_unacknowledged_command(store):
    s, _ = store
    action = {'kind':'presence','value':'idle'}
    ticket = s.prepare('admin',action)
    command = s.enqueue('admin',ticket['id'],action,True)
    assert s.claim('boot-1')['id'] == command
    assert s.claim('boot-2') is None
    assert s.command(command)['state'] == 'unknown'
    assert s.snapshot()['audit'][0]['result'] == '結果未確認'
