import json
DATA_FILE = "steps_7days.json"

# JSONロード/セーブ
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# 歩数を集計
def summarize_steps(steps: int):
    

