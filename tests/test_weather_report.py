import asyncio
import ast
import copy
import json
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import discord
from discord.ext import tasks
import requests

from feature.weather_report.forecast import (
    ForecastUnavailable, JmaForecastProvider, JST, format_forecast, parse_jma,
)
from feature.weather_report.reporter import WeatherReporter


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(
            (Path(__file__).parent / "fixtures/jma_140000.json").read_text())
        self.day = date(2026, 10, 2)

    def test_selects_target_day_and_yokohama(self):
        forecast = parse_jma(self.payload, self.day)
        self.assertEqual(forecast.weather, "くもり 昼前 から 昼過ぎ 雨")
        self.assertEqual(forecast.precipitation, ((0, "20"), (6, "50"),
                                                (12, "50"), (18, "30")))
        self.assertEqual(forecast.temperatures, ((0, "20"), (9, "22")))
        self.assertIn("06–12時 50%", format_forecast(forecast))
        self.assertIn("横浜", format_forecast(forecast))

    def test_does_not_use_another_day_or_weekly_forecast(self):
        with self.assertRaises(ForecastUnavailable):
            parse_jma(self.payload, date(2026, 10, 4))

    def test_missing_optional_values(self):
        payload = copy.deepcopy(self.payload)
        payload[0]["timeSeries"] = payload[0]["timeSeries"][:1]
        forecast = parse_jma(payload, self.day)
        self.assertIn("降水確率：情報なし", format_forecast(forecast))
        self.assertIn("予想気温：情報なし", format_forecast(forecast))

    def test_invalid_payload(self):
        for payload in ([], {}, None, [{"timeSeries": []}]):
            with self.subTest(payload=payload), self.assertRaises(ForecastUnavailable):
                parse_jma(payload, self.day)

    @patch("feature.weather_report.forecast.requests.get")
    def test_http_timeout_and_status(self, get):
        get.return_value.json.return_value = self.payload
        self.assertEqual(JmaForecastProvider().fetch(self.day).day, self.day)
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 15))
        get.return_value.raise_for_status.assert_called_once()
        get.side_effect = requests.Timeout()
        with self.assertRaises(requests.Timeout):
            JmaForecastProvider().fetch(self.day)


class ReporterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = Mock()
        self.client.wait_until_ready = AsyncMock()
        self.channel = Mock(spec=discord.TextChannel)
        self.channel.send = AsyncMock()
        self.client.get_channel.return_value = self.channel
        self.provider = Mock()
        payload = json.loads(
            (Path(__file__).parent / "fixtures/jma_140000.json").read_text())
        self.provider.fetch.return_value = parse_jma(payload, date(2026, 10, 2))
        self.reporter = WeatherReporter(self.client, 123, self.provider)

    async def test_posts_once_and_fetches_channel_on_cache_miss(self):
        self.client.get_channel.return_value = None
        self.client.fetch_channel = AsyncMock(return_value=self.channel)
        await self.reporter.post_report()
        self.client.fetch_channel.assert_awaited_once_with(123)
        self.channel.send.assert_awaited_once()

    async def test_failure_does_not_stop_next_execution(self):
        forecast = self.provider.fetch.return_value
        self.provider.fetch.side_effect = [requests.Timeout(), forecast]
        with self.assertLogs("feature.weather_report.reporter", level="ERROR"):
            await self.reporter.post_report()
        self.channel.send.assert_not_awaited()
        await self.reporter.post_report()
        self.channel.send.assert_awaited_once()

    async def test_send_failure_is_logged(self):
        self.channel.send.side_effect = RuntimeError("permission denied")
        with self.assertLogs("feature.weather_report.reporter", level="ERROR"):
            await self.reporter.post_report()

    async def test_cancellation_propagates(self):
        self.client.wait_until_ready.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.reporter.post_report()



class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # main全体の外部連携を起動せず、実際のタスクとon_readyを実行する。
        tree = ast.parse((Path(__file__).parents[1] / "main.py").read_text())
        selected = [node for node in tree.body
                    if isinstance(node, ast.AsyncFunctionDef)
                    and node.name in ("scheduled_weather_report_task", "on_ready")]
        self.reporter = Mock(post_report=AsyncMock())
        self.cfg = Mock(WEATHER_REPORT_CHANNEL_ID=123)
        self.namespace = {
            "tasks": tasks, "time": time, "JST": JST,
            "weather_reporter": self.reporter, "cfg": self.cfg,
            "client": Mock(event=lambda function: function),
            "set_presence": AsyncMock(),
            "scheduled_tech_trend_task": Mock(is_running=Mock(return_value=True)),
            "update_presence": Mock(is_running=Mock(return_value=True)),
        }
        exec(compile(ast.Module(body=selected, type_ignores=[]), "main.py", "exec"),
             self.namespace)
        self.task = self.namespace["scheduled_weather_report_task"]

    async def test_schedule_and_dispatch(self):
        self.assertEqual(self.task.time[0].hour, 7)
        self.assertEqual(str(self.task.time[0].tzinfo), "Asia/Tokyo")
        await self.task()
        self.reporter.post_report.assert_awaited_once()

    async def test_on_ready_starts_only_once(self):
        with patch.object(self.task, "start") as start:
            with patch.object(self.task, "is_running", return_value=False):
                await self.namespace["on_ready"]()
            start.assert_called_once()
            with patch.object(self.task, "is_running", return_value=True):
                await self.namespace["on_ready"]()
            start.assert_called_once()

    async def test_placeholder_disables_schedule(self):
        self.cfg.WEATHER_REPORT_CHANNEL_ID = 0
        with patch.object(self.task, "start") as start:
            await self.namespace["on_ready"]()
            start.assert_not_called()
        self.cfg.logger.warning.assert_called_once()
