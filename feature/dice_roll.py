import random
import logging


# ダイスロールを行う関数 合計値も出力
# times→ダイスを振る回数 num_faces→ダイスの面の数
# 例:dice_roll(1,100)→1d100
def dice_roll(times_list:list[int], num_faces_list:list[int])-> str:
    if len(times_list) != len(num_faces_list):
        logging.error(f"引数の読み取りに失敗しました.times_list:{times_list},num_faces_list{num_faces_list}")
        return "数字は偶数個指定してちょうだい!"

    # 10個までしかダイスを触れないようにする
    if (len(times_list) > 10) or (len(num_faces_list) > 10):
        return "1度に振れるダイスは10個までよ!"

    # 一度に100回までしかダイスを触れないようにする
    max_times = max(times_list)
    if (101 <= max_times):
        return "ダイスは1度に100回までしか振れないわ!"

    # 入力された数字の中に0や負の数が入っていた場合はエラーを出す
    for time in times_list:
        if time <= 0:
            return "振る回数は1以上を指定してちょうだい!"
    
    # ダイスの面数に0や負の数が入っていた場合はエラーを出す
    for num_faces in num_faces_list:
        if num_faces <= 0:
            return "ダイスの面数は1以上を指定してちょうだい!"


    try:
        times = len(times_list) # ダイスロールの実行回数
        total = 0 # ダイスロールの合計値
        response = "" # 応答文

        # 最初に実行文を作る
        # 例:「1d100を実行するわ！」
        response += "`"
        for i in range(times):
            response += str(times_list[i]) + "d" + str(num_faces_list[i])
            if i != (times-1):
                response += "+"
        
        response += "`を実行するわ!\n"

        
        # ダイスロール部分を作成
        for i in range(times):
            for j in range(times_list[i]):
                result = random.randint(1,num_faces_list[i])# 1〜面数でランダムに選択
                response += str(result) + " "
                total += result
            response += "  "
        
        response += ("\n合計:" + str(total))
        return response
    except TypeError as e:
        logging.error(f"{e}times_list:{times_list},num_faces_list:{num_faces_list}")
        return "内部でエラーが発生したわ!ごめんなさい!"
    except ValueError as e:
        logging.error(f"{e}:times_list:{times_list},num_faces_list:{num_faces_list}")
        return "内部でエラーが発生したわ!ごめんなさい!"

# ダイスロールを1回だけ行う関数
def dice_roll_one_times(num_faces:int) -> str:
    
    response = f"`1d{num_faces}`を実行するわ!\n"
    response += str(random.randint(1,num_faces))
    return response 
