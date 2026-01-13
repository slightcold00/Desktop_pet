@echo off
echo ========================================
echo   正在为你打包 [天成] 桌宠，请稍候...
echo ========================================

:: --noconsole: 不显示黑色控制台
:: --add-data: 强制把 food 和 emo 文件夹塞进安装包
:: Windows 下路径分隔符用分号 ;
pyinstaller --noconsole --onefile ^
    --add-data "food;food" ^
    --add-data "emo;emo" ^
    --icon=tiancheng.ico ^
    tiancheng.py

echo ========================================
echo   打包完成！请在 dist 文件夹中查看 .exe
echo   记得把 items.json 和 config.json 也放在一起哦
echo ========================================
pause