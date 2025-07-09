import json
import csv
import random

# CSVファイルを各行ごとのリストへと変換


def csvToList(csvName):
    list = []
    with open(csvName, mode='r', encoding='utf-8') as csv_file:
        for row in csv_file:
            list.append(row)
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
