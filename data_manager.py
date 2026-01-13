# data_manager.py
import json
import os
from config import DATA_PATH  # 导入 config 定义的路径

class DataManager:
    @staticmethod
    def load_json(filename, default):
        path = os.path.join(DATA_PATH, filename)
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default

    @staticmethod
    def save_json(filename, data):
        path = os.path.join(DATA_PATH, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)