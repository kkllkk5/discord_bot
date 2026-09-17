import json
import csv
import random
import re

# 課題曲生成コマンド
async def handle_iidx_practice_music(message):
    _, level, song_num = message.content.split()
    try:
        practice_music_list = make_practice_music(
            int(level), int(song_num))
        response = "以下が課題曲です!\n"
        for music in practice_music_list:
            response += (music[0])
    except Exception as e:
        response = "レベルには11,12のみを現在サポートしています"
    await message.channel.send(response)

# CSVファイルを各行ごとのリストへと変換
def csvToList(csvName):
    list = []
    with open(csvName, mode='r', encoding='utf-8') as csv_file:
        for row in csv_file:
            list_in_row = []
            for item in row.split(','):
                list_in_row.append(item)
            list.append(list_in_row)
    return list

# 課題曲をランダムに選択
# level:対象レベル（現状11,12のみサポート）
# song_num:課題曲の曲数
def make_practice_music(level, song_num):
    if level == 11:
        music_list = csvToList('songlist_11.csv')
    elif level == 12:
        music_list = csvToList('songlist_12.csv')
    else:
        raise Exception("課題曲生成は現在レベル11,12のみ対応しています")
    return random.choices(music_list, k=song_num)


# DP非公式難易度の取得
# TODO:現状は同梱したリストを元に算出しているが，定期的にデータを更新する形で最新データをネットで取得させたい
async def handle_dp_level(message,client):
    _, song_name = message.content.split()
    
    # 指定した曲名の一部が1文字だった場合は検索しない
    # (候補が非常に多くなる恐れがあるため)
    # [({楽曲名},{楽曲の非公式難易度})]
    candidate_list = search_songname_for_dp(song_name)

    # 楽曲が見つからなかった場合は，処理を終了し最初からやり直す
    if len(candidate_list) == 0:
        response = "楽曲が見つかりませんでした.曲名を確認し再度実行してください."
        await message.channel.send(response)
    # 楽曲の候補が一つしかなかった場合は，その楽曲の難易度を送信する
    elif len(candidate_list) == 1:
        response = candidate_list[0][0] + "のDP非公式難易度は" + \
            str.strip(candidate_list[0][1]) + "です."
        await message.channel.send(response)
    else:

        response = "以下の楽曲が候補です．対象の楽曲を番号で指定してください．\n"

        # 番号（1から順番に振る）と曲名を一覧で送信する
        for i, (music_name, _) in enumerate(candidate_list):
            response += "[" + str(i+1) + "]:" + music_name + "\n"

        await message.channel.send(response)

        # 待っているものに該当するかを確認する関数
        def check(m):
            # メッセージが数字かつ メッセージを送信したチャンネルが
            # コマンドを打ったチャンネルという条件
            return m.content.isdigit() and m.channel == message.channel

        try:
            while (True):
                msg = await client.wait_for('message', check=check)
                target_num = int(msg.content) - 1
                # 番号が不正(マイナスだったり，想定よりも大きな数)だった場合，送信し直してもらう
                if target_num < 0 or target_num >= len(candidate_list):
                    await message.channel.send("対象の楽曲を番号で正しく指定してください.")
                    continue
                else:
                    response = candidate_list[target_num][0] + "のDP非公式難易度は" + str.strip(
                        candidate_list[target_num][1]) + "です."
                    await message.channel.send(response)
                    break
        except ValueError as e:
            await message.channel.send("対象の楽曲を番号で指定してください.")
        except Exception as e:
            await message.channel.send("不明なエラーが発生しました.")

# DPの楽曲リストから，楽曲を検索する
# name_parts:曲名の一部
def search_songname_for_dp(name_parts):
    candidate_list = []
    # DP楽曲リストから，曲名を取得
    # (レベル情報も同時に取得されるが，今回は利用しない)
    music_list = csvToList('dp_level.csv')
    for music_info in music_list:
        music_name = music_info[0]
        music_level = music_info[1]
        if re.match('.*' + name_parts + '.*',music_name):
            candidate_list.append([music_name,music_level])
    return candidate_list
