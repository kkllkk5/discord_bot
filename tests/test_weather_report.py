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
from feature.weather_report.location import YOKOHAMA, Location, resolve_location
from feature.weather_report.narrator import GeminiForecastNarrator
from feature import gemini


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
        provider = JmaForecastProvider()
        provider._location = YOKOHAMA
        get.return_value.json.return_value = self.payload
        self.assertEqual(provider.fetch(self.day).day, self.day)
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 15))
        get.return_value.raise_for_status.assert_called_once()
        get.side_effect = requests.Timeout()
        with self.assertRaises(requests.Timeout):
            provider.fetch(self.day)

    def test_different_area_and_station(self):
        forecast = parse_jma(self.payload, self.day,
                             Location("小田原", "140000", "140020", "小田原"))
        self.assertEqual(forecast.precipitation[1], (6, "40"))
        self.assertEqual(forecast.temperatures, ((0, "19"), (9, "23")))
        self.assertIn("小田原の天気予報", format_forecast(forecast))
        self.assertEqual(forecast.area_name, "西部")

    def test_missing_station_does_not_use_other_city(self):
        forecast = parse_jma(self.payload, self.day,
                             Location("川崎市", "140000", "140010", "川崎"))
        self.assertEqual(forecast.temperatures, ())
        self.assertIn("予想気温：情報なし", format_forecast(forecast))


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(
            (Path(__file__).parent / "fixtures/jma_areas.json").read_text())

    def test_major_city_names_and_municipality(self):
        for name, office, area, station in [
            ("横浜", "140000", "140010", "横浜"),
            ("東京", "130000", "130010", "東京"),
            ("大阪", "270000", "270000", "大阪"),
            ("京都", "260000", "260010", "京都"),
            ("神奈川県/小田原市", "140000", "140020", "小田原"),
            ("新宿区", "130000", "130010", "新宿区"),
        ]:
            with self.subTest(name=name):
                result = resolve_location(self.catalog, name)
                self.assertEqual((result.office_code, result.area_code, result.station_name),
                                 (office, area, station))

    def test_explicit_station(self):
        self.assertEqual(resolve_location(self.catalog, "新宿区", "東京").station_name, "東京")

    def test_unknown_ambiguous_and_empty_names(self):
        for name in ("存在しない地点", "神奈川県", "", "東京都"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                resolve_location(self.catalog, name)

    @patch("feature.weather_report.forecast.requests.get")
    def test_provider_resolves_once_and_uses_selected_office(self, get):
        payload = json.loads((Path(__file__).parent / "fixtures/jma_140000.json").read_text())
        catalog_response = Mock()
        catalog_response.json.return_value = self.catalog
        forecast_response = Mock()
        forecast_response.json.return_value = payload
        get.side_effect = [catalog_response, forecast_response, forecast_response]
        provider = JmaForecastProvider("小田原")
        provider.fetch(date(2026, 10, 2))
        provider.fetch(date(2026, 10, 2))
        self.assertEqual(get.call_count, 3)
        self.assertTrue(get.call_args_list[1].args[0].endswith("140000.json"))
        self.assertEqual(provider._location.area_code, "140020")


class NarratorTests(unittest.TestCase):
    def setUp(self):
        payload = json.loads((Path(__file__).parent / "fixtures/jma_140000.json").read_text())
        self.forecast = parse_jma(payload, date(2026, 10, 2))

    @patch("feature.weather_report.narrator.gemini.analyze_with_gemini")
    def test_passes_forecast_and_persona(self, generate):
        generate.return_value = "花海咲季よ！今日は雨に備えてね！"
        text = GeminiForecastNarrator().narrate(self.forecast)
        self.assertTrue(text.startswith("花海咲季よ！"))
        contents, config = generate.call_args.args
        self.assertIn("06–12時 50%", contents[0])
        self.assertIn("横浜", contents[0])
        self.assertIn("日最低・最高", config.system_instruction)
        self.assertEqual(config.http_options.timeout, 15000)
        self.assertTrue(generate.call_args.kwargs["raise_on_failure"])

    @patch("feature.weather_report.narrator.gemini.analyze_with_gemini")
    def test_rejects_missing_persona_and_oversized_text(self, generate):
        for text in ("", "天気です", "花海咲季よ！" + "あ" * 500):
            with self.subTest(text=text[:10]), self.assertRaises(ValueError):
                generate.return_value = text
                GeminiForecastNarrator().narrate(self.forecast)

    @patch("feature.gemini.get_client")
    def test_shared_helper_failure_modes(self, client):
        client.return_value.models.generate_content.side_effect = RuntimeError("unavailable")
        with self.assertLogs(level="ERROR"):
            with self.assertRaises(RuntimeError):
                gemini.analyze_with_gemini([], None, raise_on_failure=True)
            self.assertIn("一時的に利用できない", gemini.analyze_with_gemini([], None))

    @patch("feature.gemini.get_client")
    def test_empty_gemini_response_retries(self, client):
        client.return_value.models.generate_content.side_effect = [
            Mock(text=None), Mock(text="花海咲季よ！")]
        with self.assertLogs(level="ERROR"):
            self.assertEqual(gemini.analyze_with_gemini([], None, raise_on_failure=True),
                             "花海咲季よ！")


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

    async def test_narration_is_posted_with_original_forecast(self):
        self.reporter.narrator = Mock()
        self.reporter.narrator.narrate.return_value = "花海咲季よ！雨に備えるのよ！"
        await self.reporter.post_report()
        text = self.channel.send.call_args.args[0]
        self.assertIn("花海咲季よ！", text)
        self.assertIn("06–12時 50%", text)
        self.assertIn("出典：気象庁", text)
        self.assertFalse(self.channel.send.call_args.kwargs["allowed_mentions"].everyone)

    async def test_narration_failure_falls_back_to_original_forecast(self):
        self.reporter.narrator = Mock()
        self.reporter.narrator.narrate.side_effect = RuntimeError("Gemini failed")
        with self.assertLogs("feature.weather_report.reporter", level="ERROR"):
            await self.reporter.post_report()
        self.assertEqual(self.channel.send.call_args.args[0],
                         format_forecast(self.provider.fetch.return_value))

    async def test_oversized_narration_falls_back(self):
        self.reporter.narrator = Mock()
        self.reporter.narrator.narrate.return_value = "あ" * 2000
        with self.assertLogs("feature.weather_report.reporter", level="ERROR"):
            await self.reporter.post_report()
        self.assertEqual(self.channel.send.call_args.args[0],
                         format_forecast(self.provider.fetch.return_value))



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
