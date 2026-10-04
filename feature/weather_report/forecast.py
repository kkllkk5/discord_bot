"""気象庁データの取得、当日予報の抽出、表示を分離する。"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

import requests

JST = ZoneInfo("Asia/Tokyo")
JMA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/140000.json"
SOURCE_URL = "https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code=140000"


class ForecastUnavailable(ValueError):
    """対象日の予報がない、または取得形式が変わった。"""


@dataclass(frozen=True)
class Forecast:
    day: date
    weather: str
    wind: str
    precipitation: tuple[tuple[int, str], ...]
    temperatures: tuple[tuple[int, str], ...]
    reported_at: datetime


class ForecastProvider(Protocol):
    def fetch(self, day: date) -> Forecast: ...


def parse_jma(payload: list, day: date) -> Forecast:
    """東部(140010)の天気・降水確率と横浜(46106)の気温を抽出。"""
    try:
        report = payload[0]
        weather = None
        wind = "情報なし"
        precipitation = []
        temperatures = []
        for series in report["timeSeries"]:
            times = [datetime.fromisoformat(t).astimezone(JST)
                     for t in series["timeDefines"]]
            for area in series["areas"]:
                code = area["area"]["code"]
                for index, instant in enumerate(times):
                    if instant.date() != day:
                        continue
                    if code == "140010":
                        if "weathers" in area:
                            weather = " ".join(area["weathers"][index].split())
                            if "winds" in area:
                                wind = " ".join(area["winds"][index].split())
                        if "pops" in area:
                            precipitation.append((instant.hour, area["pops"][index]))
                    if code == "46106" and "temps" in area:
                        temperatures.append((instant.hour, area["temps"][index]))
        if not weather:
            raise ForecastUnavailable(f"{day}の横浜近辺の予報がありません")
        return Forecast(day, weather, wind, tuple(precipitation),
                        tuple(temperatures), datetime.fromisoformat(report["reportDatetime"]))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ForecastUnavailable(f"気象庁の対象日予報を読み取れません: {day}") from exc


class JmaForecastProvider:
    def fetch(self, day: date) -> Forecast:
        response = requests.get(JMA_URL, timeout=(5, 15))
        response.raise_for_status()
        return parse_jma(response.json(), day)


def format_forecast(forecast: Forecast) -> str:
    lines = [f"🌤️ 横浜近辺の天気予報（{forecast.day:%Y/%m/%d}）",
             "対象：神奈川県東部 / 気温：横浜", f"天気：{forecast.weather}",
             f"風：{forecast.wind}"]
    pops = " / ".join(
        f"{hour:02d}–{hour + 6:02d}時 {value + '%' if value else '情報なし'}"
        for hour, value in forecast.precipitation)
    lines.append(f"降水確率：{pops or '情報なし'}")
    # 気象庁の短期予報は時刻ごとの値。日最低/最高と誤って扱わない。
    temps = " / ".join(
        f"{hour:02d}時 {value + '℃' if value else '情報なし'}"
        for hour, value in forecast.temperatures)
    lines.append(f"予想気温：{temps or '情報なし'}")
    lines.append(f"発表：{forecast.reported_at.astimezone(JST):%m/%d %H:%M} JST")
    lines.append(f"出典：気象庁 {SOURCE_URL}")
    return "\n".join(lines)
