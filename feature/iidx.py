import json
import csv
import random
import re

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

# DPの楽曲リストから，楽曲を検索する
# name_parts:曲名の一部
def search_songname_for_dp(name_parts):
    candidate_list = []
    # DP楽曲リストから，曲名を取得
    # (レベル情報も同時に取得されるが，今回は利用しない)
    music_list = csvToList('dp_level.csv')
    for music_info in music_list:
        music_name = music_info[0]
        if re.match('.*' + name_parts + '.*',music_name):
            candidate_list.append(music_name)
    return candidate_list
