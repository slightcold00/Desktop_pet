# config.py
import sys
import os
import platform

# 系统判断
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# 资源路径
if getattr(sys, 'frozen', False):
    if IS_MAC:
        RES_PATH = os.path.join(os.path.dirname(sys.executable), "..", "Resources")
    else:
        RES_PATH = sys._MEIPASS
else:
    RES_PATH = os.path.dirname(os.path.abspath(__file__))

# 数据路径
if getattr(sys, 'frozen', False):
    executable_path = os.path.abspath(sys.executable)
    if IS_MAC:
        DATA_PATH_0 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(executable_path))))
    else:
        DATA_PATH_0 = os.path.dirname(executable_path)
else:
    DATA_PATH_0 = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(DATA_PATH_0, "data")

# 确保 data 目录存在
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)