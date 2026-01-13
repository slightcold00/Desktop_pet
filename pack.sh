#!/bin/zsh
echo "正在为天成进行 Mac 封装..."
source venv/bin/activate
pyinstaller --noconsole --windowed \
    --name "DesktopPet" \
    --add-data "data:data" \
    --add-data "emo:emo" \
    --add-data "food:food" \
    --icon "res/icon.icns" \
    --clean \
    tiancheng.py
