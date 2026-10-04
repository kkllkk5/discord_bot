"""気象庁の地域一覧から設定された地域名を予報区域に解決する。"""

from dataclasses import dataclass

AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"


@dataclass(frozen=True)
class Location:
    """表示する地点と、取得・抽出に必要な気象庁の識別情報。"""

    name: str  # 設定された地域名。投稿の見出しに使用する。
    office_code: str  # 予報JSONの取得先を決める府県予報区コード。
    area_code: str  # JSONから天気・降水確率を選ぶ一次細分区域コード。
    station_name: str  # 気温を選ぶ観測地点名。存在確認は予報の解析時に行う。


YOKOHAMA = Location("横浜", "140000", "140010", "横浜")


# 地域名を1つの予報区域に解決する。通信や入力データの変更は行わない。
#
# catalogには気象庁area.jsonの階層と親子関係が揃っていることを前提とする。
# nameは地域名または「都道府県/地域名」。空・不明・曖昧な名前はValueError。
# station_nameがNoneなら地域名から推定するが、観測地点の存在は保証しない。
def resolve_location(catalog: dict, name: str, station_name: str | None = None) -> Location:
    name = name.strip()
    if not name:
        raise ValueError("天気予報の地域名が空です")
    parts = name.split("/")
    if len(parts) > 2:
        raise ValueError("地域名は『都道府県/地域名』の形式で指定してください")
    region = parts[-1]
    # 同名の市町村を区別するための任意の府県予報区名。
    office_filter = parts[0] if len(parts) == 2 else None
    # 主要都市の通称。東京は島しょ部と区別し、横浜は青森の横浜町と区別する。
    lookup = {"東京": "東京地方", "横浜": "横浜市北部",
              "横浜市": "横浜市北部"}.get(region, region)
    # (府県予報区コード, 一次細分区域コード) -> 府県予報区名。
    # 同じ予報区域に属する複数の市町村を1候補にまとめる。
    matches = {}
    # 市町村が一致するなら県の省略名より優先する（例: 福岡市と福岡県）。
    for group in ("class20s", "class15s", "class10s", "offices"):
        for code, entry in catalog[group].items():
            short_name = entry["name"]
            if short_name.endswith(("都", "道", "府", "県", "市", "町", "村")):
                short_name = short_name[:-1]
            if lookup not in (entry["name"], short_name):
                continue
            if group == "offices":
                areas = entry["children"]
            elif group == "class10s":
                areas = [code]
            elif group == "class15s":
                areas = [entry["parent"]]
            else:
                # class20s(市町村) -> class15s(二次細分区域) -> class10s(一次細分区域)。
                areas = [catalog["class15s"][entry["parent"]]["parent"]]
            for area_code in areas:
                office_code = catalog["class10s"][area_code]["parent"]
                office = catalog["offices"][office_code]["name"]
                if office_filter and office_filter not in (office, office[:-1]):
                    continue
                matches[(office_code, area_code)] = office
        if matches:
            break
    if len(matches) != 1:
        if not matches:
            raise ValueError(f"気象庁の地域一覧に『{name}』がありません")
        choices = [f"{office}/{catalog['class10s'][area]['name']}"
                   for (_, area), office in matches.items()]
        raise ValueError(f"『{name}』は複数の予報区域に該当します: {', '.join(choices)}")
    office_code, area_code = next(iter(matches))
    if station_name is None:
        station_name = region
        if len(station_name) > 2 and station_name.endswith(("都", "道", "府", "県", "市", "町", "村")):
            station_name = station_name[:-1]
    return Location(name, office_code, area_code, station_name)
