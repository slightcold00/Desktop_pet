# main.py
import sys
from PyQt5.QtWidgets import QApplication, QStyleFactory
from tiancheng_pet import DesktopPet

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置风格
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 启动桌宠
    pet = DesktopPet()
    pet.show()
    
    sys.exit(app.exec_())