#!/bin/zsh
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 tiancheng.py
else
    echo "找不到虚拟环境，请先运行 ./install.sh"
fi
