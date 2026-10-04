"""気象庁データの取得、当日予報の抽出、表示を分離する。"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

import requests
from .location import AREA_URL, Location, YOKOHAMA, resolve_location

JST = ZoneInfo("Asia/Tokyo")


class ForecastUnavailable(ValueError):
    """対象日の予報がない、または取得形式が変わった。"""


@dataclass(frozen=True)
class Forecast:
    """指定日の予報。数値文字列は気象庁の値を保ち、空文字は欠測を表す。"""

    day: date
    weather: str
    wind: str
    precipitation: tuple[tuple[int, str], ...]  # (JSTの6時間枠の開始時, 降水確率[%])。
    temperatures: tuple[tuple[int, str], ...]  # (JSTの予報時刻の時, 気温[℃])。日最低・最高ではない。
    reported_at: datetime  # 気象庁の発表日時。タイムゾーン付き。
    location: Location = YOKOHAMA
    area_name: str = "神奈川県東部"  # 実際に抽出した天気の予報区域名。
    station_name: str = "横浜"  # 実際に抽出した気温の観測地点名。未取得なら「情報なし」。


class ForecastProvider(Protocol):
    # JSTでの対象日を受け取り予報を返す。取得・解析失敗は例外で通知する。
    #
    # 同期処理のため、非同期の呼び出し元はイベントループ外で実行する。
    def fetch(self, day: date) -> Forecast:
        ...


# 気象庁の予報JSONから、day(JST)とlocationに一致する値を抽出する。
#
# payloadは取得済みJSON。通信や入力データの変更は行わない。
# 天気がない日や形式不正はForecastUnavailable。風・降水確率・気温は
# 欠測を許容し、別の日・区域・観測地点の値では補完しない。
def parse_jma(payload: list, day: date, location: Location = YOKOHAMA) -> Forecast:
    try:
        report = payload[0]  # 短期予報。後続の週間予報を代替値に使用しない。
        weather = None
        wind = "情報なし"
        precipitation = []
        temperatures = []
        area_name = ""
        station_name = "情報なし"
        for series in report["timeSeries"]:
            # timeDefinesと各項目の配列は同じ添字で対応している。
            times = [datetime.fromisoformat(t).astimezone(JST)
                     for t in series["timeDefines"]]
            for area in series["areas"]:
                code = area["area"]["code"]
                for index, instant in enumerate(times):
                    if instant.date() != day:
                        continue
                    if code == location.area_code:
                        area_name = area["area"]["name"]
                        if "weathers" in area:
                            weather = " ".join(area["weathers"][index].split())
                            if "winds" in area:
                                wind = " ".join(area["winds"][index].split())
                        if "pops" in area:
                            precipitation.append((instant.hour, area["pops"][index]))
                    if area["area"]["name"] == location.station_name and "temps" in area:
                        station_name = area["area"]["name"]
                        temperatures.append((instant.hour, area["temps"][index]))
        if not weather:
            raise ForecastUnavailable(f"{day}の{location.name}の予報がありません")
        return Forecast(day, weather, wind, tuple(precipitation),
                        tuple(temperatures), datetime.fromisoformat(report["reportDatetime"]),
                        location, area_name, station_name)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ForecastUnavailable(f"気象庁の対象日予報を読み取れません: {day}") from exc


class JmaForecastProvider:
    # 設定を保持するだけで通信しない。地域の解決は初回fetchまで遅延する。
    def __init__(self, location_name: str = "横浜", station_name: str | None = None):
        self.location_name = location_name
        self.station_name = station_name
        self._location = None  # 解決済み地域のキャッシュ。成功後は同一インスタンスで再利用。

    # 指定日の予報を同期取得する。地域解決・HTTP・解析の例外は呼び出し元へ返す。
    #
    # 初回のみ地域一覧も取得する。タイムアウトは接続5秒・読み取り15秒で、
    # 処理全体の制限時間ではない。設定変更時はインスタンスを作り直す。
    def fetch(self, day: date) -> Forecast:
        if self._location is None:
            catalog = requests.get(AREA_URL, timeout=(5, 15))
            catalog.raise_for_status()
            self._location = resolve_location(catalog.json(), self.location_name, self.station_name)
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{self._location.office_code}.json"
        response = requests.get(url, timeout=(5, 15))
        response.raise_for_status()
        return parse_jma(response.json(), day, self._location)


# 予報を出典付きの投稿文に変換する純粋関数。欠測値は「情報なし」と表示する。
def format_forecast(forecast: Forecast) -> str:
    lines = [f"🌤️ {forecast.location.name}の天気予報（{forecast.day:%Y/%m/%d}）",
             f"対象：{forecast.area_name} / 気温：{forecast.station_name}", f"天気：{forecast.weather}",
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
    source_url = f"https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={forecast.location.office_code}"
    lines.append(f"出典：気象庁 {source_url}")
    return "\n".join(lines)
