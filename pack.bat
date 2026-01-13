@echo off
:: 1. 激活虚拟环境 (确保安装了 pyinstaller)
call .\venv\Scripts\activate

:: 2. 运行打包命令
pyinstaller --noconsole --windowed ^
    --name "DesktopPet" ^
    --icon "icon/tiancheng.ico" ^
    --add-data "data;data" ^
    --add-data "icon;icon" ^
    --add-data "emo;emo" ^
    --add-data "food;food" ^
    --clean ^
    main.py

echo 打包完成啦！
pause