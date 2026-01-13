#!/bin/zsh
echo "开始配置 Mac 环境..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install PyQt5 requests psutil pyobjc-framework-Cocoa pyinstaller
echo "环境配置完成！"
