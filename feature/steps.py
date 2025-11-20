

# 「歩数集計用」チャンネル
STEPS_FOR_SUMMARY_CHANEL_ID = "1423994718743957515"
channel = client.get_channel(STEPS_FOR_SUMMARY_CHANNEL_ID)

# 直近の歩数平均を集計
def get_ave_recent_steps():
    # デフォルト:7日間（メッセージ7件）
    DAYS = 7
    sum_steps = 0

    msg_list = channel.history(limit = DAYS)
    # 「歩数集計用」
    for msg in msg_list:
        try:
            sum_steps += int(msg)
        except Exception as e:
            raise e
    return sum_steps/len(msg_list)

# 当日の歩数を取得
def get_today_steps():
    return channel.history(limit = 1)

