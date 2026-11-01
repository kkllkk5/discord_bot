"""通信障害後もヘルスチェックが次の周期で再実行されることを検証する。"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import requests
import schedule

import server


def make_response(status):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status_code = status
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError()
    return response


@pytest.mark.parametrize('failure', [
    requests.ConnectionError('Connection reset by peer'),
    requests.ConnectTimeout(),
    requests.ReadTimeout(),
    requests.HTTPError(),
])
def test_scheduler_continues_after_request_failure(monkeypatch, caplog, failure):
    response = make_response(200)
    get = MagicMock(side_effect=[failure, response])
    monkeypatch.setattr(server.requests, 'get', get)
    scheduler = schedule.Scheduler()
    job = scheduler.every(1).minutes.do(server.health_check)

    job.next_run = datetime.now() - timedelta(seconds=1)
    scheduler.run_pending()
    assert job.next_run > datetime.now()
    assert 'retrying on the next interval' in caplog.text

    job.next_run = datetime.now() - timedelta(seconds=1)
    scheduler.run_pending()
    assert get.call_count == 2
    get.assert_called_with(server.HEALTH_CHECK_URL, timeout=(5, 10))
    response.__exit__.assert_called_once()


def test_http_failure_is_logged_and_response_closed(monkeypatch, caplog):
    response = make_response(503)
    monkeypatch.setattr(server.requests, 'get', MagicMock(return_value=response))
    assert server.health_check() is None
    assert 'HTTPError' in caplog.text
    response.__exit__.assert_called_once()


def test_success_returns_status(monkeypatch):
    response = make_response(200)
    monkeypatch.setattr(server.requests, 'get', MagicMock(return_value=response))
    assert server.health_check() == 200
    response.raise_for_status.assert_called_once()
    response.__exit__.assert_called_once()
