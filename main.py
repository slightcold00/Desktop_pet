# main.py
import sys
from PyQt5.QtWidgets import QApplication, QStyleFactory
from tiancheng_pet import DesktopPet
import ctypes
from config import IS_WINDOWS

if __name__ == "__main__":
    # 💡 只有在 Windows 下才运行这段逻辑
    if IS_WINDOWS:
        try:
            # 给你的应用起一个独一无二的名字（比如：公司名.产品名.版本号）
            myappid = 'myteam.tiancheng.desktoppet.1.0' 
            # 告诉系统，这个进程有自己的 App ID，不要把它和 Python 混为一谈
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Windows AppID Error: {e}")
    app = QApplication(sys.argv)
    
    # 设置风格
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 启动桌宠
    pet = DesktopPet()
    pet.show()
    
    sys.exit(app.exec_())