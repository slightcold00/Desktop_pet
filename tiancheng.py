# -*- coding: utf-8 -*-
import sys, os, json, time, random, threading, requests, psutil, ctypes, subprocess

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QMenu, QAction, QDialog, QTextEdit, 
                             QFormLayout, QScrollArea, QGridLayout, QComboBox, QFileDialog, 
                             QFrame, QTabWidget, QSpinBox, QColorDialog, QInputDialog, QTextBrowser, QSizePolicy, QMessageBox, QStyleFactory)
from PyQt5.QtGui import QMovie, QColor, QFont, QTextCursor, QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint, pyqtSignal, QEvent, QLocale

import asyncio

import platform

# 💡 定义一个变量方便后面判断
# 💡 必须这样定义，Mac 的系统名是 'Darwin'，不是 'Windows'
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# 为了保险，你在下面加一行打印，运行 run.sh 时看看输出什么
#print(f"DEBUG: 当前系统是 Windows 吗？ {IS_WINDOWS}")



# 🛡️ 保护 Windows 特有库
if IS_WINDOWS:
    try:
        import win32gui
        import winsdk
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    except ImportError:
        print("Windows 库加载失败，请检查是否安装了 pywin32 和 winsdk")

# --- 1. 资源路径 (图片、图标等打包进去的) ---
if getattr(sys, 'frozen', False):
    if platform.system() == "Darwin": # macOS
        # Mac 封装后资源通常在包内的 Resources 文件夹
        RES_PATH = os.path.join(os.path.dirname(sys.executable), "..", "Resources")
    else: # Windows
        RES_PATH = sys._MEIPASS
else:
    RES_PATH = os.path.dirname(os.path.abspath(__file__))

# --- 2. 数据路径 (config.json, items.json) ---
if getattr(sys, 'frozen', False):
    # 【打包模式】
    executable_path = os.path.abspath(sys.executable)
    if platform.system() == "Darwin":
        # 💡 Mac 专用“四级跳”：
        # 1.从可执行文件跳到 MacOS -> 2.跳到 Contents -> 3.跳到 .app -> 4.跳到 dist 文件夹
        DATA_PATH_0 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(executable_path))))
    else:
        # Windows 只需要跳一级（在 .exe 旁边）
        DATA_PATH_0 = os.path.dirname(executable_path)
else:
    # 【开发调试模式】
    # 就在你的 tiancheng.py 旁边
    DATA_PATH_0 = os.path.dirname(os.path.abspath(__file__))

# 💡 统一指向 data 子文件夹
# 这样你代码里读文件时，就不用到处写 "data/" 啦
DATA_PATH = os.path.join(DATA_PATH_0, "data")



# ================= 1. 强化的数据中心 =================
class DataManager:
    @staticmethod
    def load_json(filename, default):
        # 💡 强制使用 DATA_PATH，这样它才会读 exe 旁边的文件
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
            
            
# ================= 听歌功能 (多平台格式统一版) =================
class MusicMonitor:
    def __init__(self):
        self.last_song = ""

    async def get_media_info(self):
        """
        统一返回格式: "Title - Artist"
        如果没在播放或获取失败，统一返回: None
        """
        
        # ---------------- Windows 逻辑 ----------------
        if IS_WINDOWS:
            try:
                # 1. 获取会话
                sessions = await SessionManager.request_async()
                current_session = sessions.get_current_session()
                
                if current_session:
                    # 2. 获取属性
                    properties = await current_session.try_get_media_properties_async()
                    title = properties.title
                    artist = properties.artist
                    
                    # 3. 格式化输出
                    if title and artist:
                        return f"{title} - {artist}"
                    elif title:
                        return title
                        
                return None
            except Exception as e:
                print(f"Win Media Error: {e}")
                return None

        # ---------------- Mac 逻辑 ----------------
        elif IS_MAC:
            # AppleScript: 强制拼接成 "Title - Artist" 字符串返回
            script = '''
            tell application "Music"
                if it is running then
                    if player state is playing then
                        set t_name to name of current track
                        set t_artist to artist of current track
                        return (t_name & " - " & t_artist)
                    else
                        return "Music is running but not playing"
                    end if
                else
                    return "Music app is NOT running"
                end if
            end tell
            '''
            
            try:
                # 执行脚本
                result = subprocess.run(
                    ['osascript', '-e', script], 
                    capture_output=True, 
                    text=True
                )
                
                # 4. 清洗数据 (去除 AppleScript 可能带来的换行符)
                output = result.stdout.strip()
                
                # 调试打印 (测试成功后可注释掉)
                # print(f"DEBUG_MAC_RAW: [{output}]")

                if output and output != "null" and output != "missing value":
                    return output
                
                return None
                
            except Exception as e:
                print(f"Mac Media Error: {e}")
                return None
        
        return None

# ================= 设置中心 (功能完善) =================

class UnifiedSettings(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.setWindowTitle("系统设置中心")
        self.resize(550, 650)
        self.layout = QVBoxLayout(self); self.tabs = QTabWidget()
        self.temp_config = parent.config.copy()
        
        # --- Tab 1: 连接与大小 ---
        self.tab_api = QWidget(); api_l = QFormLayout(self.tab_api)
        self.api_url = QLineEdit(self.temp_config.get("api_url", "")); self.api_key = QLineEdit(self.temp_config.get("api_key", ""))
        self.model_combo = QComboBox(); self.model_combo.addItem(self.temp_config.get("model", "gpt-3.5-turbo"))
        
        test_layout = QHBoxLayout()
        btn_fetch = QPushButton("1. 获取模型列表"); btn_fetch.clicked.connect(self.fetch_models)
        btn_test_msg = QPushButton("2. 发送测试对话"); btn_test_msg.clicked.connect(self.send_test_message)
        test_layout.addWidget(btn_fetch); test_layout.addWidget(btn_test_msg)
        
        # 在定义组件的代码块中：

        # --- 1. 桌宠像素大小 ---
        self.pet_size = QSpinBox()
        # 💡 核心：强制这个组件使用“C”语言环境（即最纯净的英文/数字环境）
        # 这样它就不会去查中文系统的数字格式了
        self.pet_size.setLocale(QLocale(QLocale.C)) 
        self.pet_size.setRange(100, 800)
        self.pet_size.setValue(int(self.temp_config.get("pet_size", 200)))

        # 💡 换一个绝对不会乱码的数字专用字体：Consolas
        # 它是 Windows 自带的编程字体，对数字的支持是最好的
        # 💡 修改后的字体设置 (兼容 Mac 和 Win)
        if platform.system() == "Darwin":
            safe_font = QFont("Monaco", 11) # Mac 的代码字体
        else:
            safe_font = QFont("Consolas", 11) # Win 的代码字体
        self.pet_size.setFont(safe_font)
        self.pet_size.lineEdit().setFont(safe_font)
        # 强制锁定 QSS 样式，不让系统主题干扰
        self.pet_size.setStyleSheet(f"font-family: '{safe_font.family()}'; qproperty-alignment: 'AlignCenter';")

        # --- 2. 全局字体大小 ---
        self.font_size = QSpinBox()
        self.font_size.setLocale(QLocale(QLocale.C))
        self.font_size.setRange(10, 50)
        self.font_size.setValue(int(self.temp_config.get("font_size", 14)))
        self.font_size.setFont(safe_font)
        self.font_size.lineEdit().setFont(safe_font)
        self.font_size.setStyleSheet("font-family: 'Consolas'; qproperty-alignment: 'AlignCenter';")

        # --- 3. 对话记忆长度 ---
        self.max_history = QSpinBox()
        self.max_history.setLocale(QLocale(QLocale.C))
        self.max_history.setRange(1, 50)
        self.max_history.setValue(int(self.temp_config.get("max_history", 10)))
        self.max_history.setFont(safe_font)
        self.max_history.lineEdit().setFont(safe_font)
        self.max_history.setStyleSheet("font-family: 'Consolas'; qproperty-alignment: 'AlignCenter';")
                
        self.current_bg = self.temp_config.get("dialog_bg", "#ffffff"); self.current_border = self.temp_config.get("dialog_border", "#000000")
        btn_bg = QPushButton("选择气泡颜色"); btn_bg.clicked.connect(lambda: self.pick_color('bg'))
        btn_bd = QPushButton("选择边框颜色"); btn_bd.clicked.connect(lambda: self.pick_color('bd'))
        
        api_l.addRow("API URL:", self.api_url); api_l.addRow("API Key:", self.api_key)
        api_l.addRow("连通性测试:", test_layout)
        api_l.addRow("模型选择:", self.model_combo)
        api_l.addRow(QFrame())
        api_l.addRow("桌宠像素大小:", self.pet_size); api_l.addRow("全局字体大小:", self.font_size)
        api_l.addRow("对话记忆长度:", self.max_history)
        api_l.addRow("底色设置:", btn_bg); api_l.addRow("边框设置:", btn_bd)

        # --- Tab 2 & 3: 角色设定与档案 ---
        self.tab_char = QWidget(); char_l = QFormLayout(self.tab_char)
        self.c_name = QLineEdit(self.temp_config.get("char_name", "")); self.c_sex = QLineEdit(self.temp_config.get("char_gender", ""))
        self.c_call = QLineEdit(self.temp_config.get("char_call_user", "")); self.c_extra = QTextEdit(); self.c_extra.setPlainText(self.temp_config.get("char_extra", ""))
        char_l.addRow("角色名字:", self.c_name); char_l.addRow("角色性别:", self.c_sex); char_l.addRow("对我的称呼:", self.c_call); char_l.addRow("补充人设:", self.c_extra)

        self.tab_user = QWidget(); user_l = QFormLayout(self.tab_user)
        self.u_name = QLineEdit(self.temp_config.get("user_name", "")); self.u_sex = QLineEdit(self.temp_config.get("user_gender", ""))
        self.u_rel = QLineEdit(self.temp_config.get("user_relation", "")); self.u_extra = QTextEdit(); self.u_extra.setPlainText(self.temp_config.get("user_extra", ""))
        user_l.addRow("我的名字:", self.u_name); user_l.addRow("我的性别:", self.u_sex); user_l.addRow("我们的关系:", self.u_rel); user_l.addRow("我的背景:", self.u_extra)

        self.tabs.addTab(self.tab_api, "连接与大小"); self.tabs.addTab(self.tab_char, "角色设定"); self.tabs.addTab(self.tab_user, "我的档案")
        self.layout.addWidget(self.tabs)
        btn_save = QPushButton("✅ 保存全部设置并刷新"); btn_save.setFixedHeight(45); btn_save.clicked.connect(self.save_all)
        self.layout.addWidget(btn_save)
        
        # 💡 新增：记录是否开启了听歌模式
        self.is_listening_music = False 
        self.current_music = ""
        

    def fetch_models(self):
        try:
            h = {"Authorization": f"Bearer {self.api_key.text()}"}
            r = requests.get(f"{self.api_url.text()}/models", headers=h, timeout=5).json()
            ms = [m["id"] for m in r["data"]]; self.model_combo.clear(); self.model_combo.addItems(ms)
            QMessageBox.information(self, "成功", "模型列表刷新成功！")
        except Exception as e: QMessageBox.critical(self, "失败", f"获取失败: {e}")

    def send_test_message(self):
        if not self.api_key.text(): return
        try:
            h = {"Authorization": f"Bearer {self.api_key.text()}"}
            data = {"model": self.model_combo.currentText(), "messages": [{"role": "user", "content": "你好"}]}
            r = requests.post(f"{self.api_url.text()}/chat/completions", headers=h, json=data, timeout=10).json()
            if 'choices' in r: QMessageBox.information(self, "成功", f"收到回复: {r['choices'][0]['message']['content']}")
            else: QMessageBox.critical(self, "失败", str(r))
        except Exception as e: QMessageBox.critical(self, "出错", str(e))

    def pick_color(self, t):
        col = QColorDialog.getColor(QColor(self.current_bg if t=='bg' else self.current_border), self)
        if col.isValid():
            if t == 'bg': self.current_bg = col.name()
            else: self.current_border = col.name()

    def save_all(self):
        import platform # 确保开头导入了
        
        # 1. 更新父窗口的配置字典
        self.parent.config.update({
            "api_url": self.api_url.text(), "api_key": self.api_key.text(), "model": self.model_combo.currentText(),
            "pet_size": self.pet_size.value(), "font_size": self.font_size.value(), "max_history": self.max_history.value(),
            "dialog_bg": self.current_bg, "dialog_border": self.current_border,
            "char_name": self.c_name.text(), "char_gender": self.c_sex.text(), "char_call_user": self.c_call.text(), "char_extra": self.c_extra.toPlainText(),
            "user_name": self.u_name.text(), "user_gender": self.u_sex.text(), "user_relation": self.u_rel.text(), "user_extra": self.u_extra.toPlainText()
        })
        
        # 2. 保存到本地文件
        DataManager.save_json("config.json", self.parent.config)

        # 💡 3. 针对 Mac 的特殊清洁逻辑 (关键修复！)
        if platform.system() == "Darwin":
            # 确认主窗口确实有 self.pet 这个属性
            if hasattr(self.parent, 'pet'):
                self.parent.pet.clear()      # 先擦掉旧图
                self.parent.pet.repaint()    # 强制立刻重绘空背景
            self.parent.repaint()            # 强制重绘整个主窗口

        # 4. 应用新样式并关闭
        self.parent.apply_styles()
        self.accept()
        

class ShopBackpackDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("美食商店")
        self.resize(550, 600)
        layout = QVBoxLayout(self)
        
        # --- 顶部状态栏：只读取，不写入 ---
        top = QHBoxLayout()
        
        # 1. 金币标签
        self.gold_label = QLabel(f"💰 金币: {self.parent.items.get('gold', 0)}")
        self.gold_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #D4AF37;") # 金色字体
        
        # 2. 💡 新增：心情标签
        mood_val = self.parent.items.get("mood", 80)
        # 根据心情值显示不同的图标
        if mood_val >= 70: mood_icon = "😊"
        elif mood_val >= 30: mood_icon = "😐"
        else: mood_icon = "😭"
        
        self.mood_label = QLabel(f"{mood_icon} 心情: {mood_val}")
        self.mood_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #FF69B4;") # 粉色字体
        
        # 3. 签到按钮
        btn_sign = QPushButton("📅 每日签到")
        btn_sign.setFixedWidth(100)
        btn_sign.clicked.connect(self.daily_check_in)
        
        # 布局排列
        top.addWidget(self.gold_label)
        top.addSpacing(20) # 间距
        top.addWidget(self.mood_label)
        top.addStretch() # 弹簧把签到推到最右边
        top.addWidget(btn_sign)
        
        layout.addLayout(top)

        # 商店区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # 💡 只负责画图，不负责加钱
        self.refresh_shop()

    def refresh_shop(self):
        # 清空旧布局
        for i in reversed(range(self.grid.count())): 
            w = self.grid.itemAt(i).widget()
            if w: w.setParent(None)
            
        items = self.parent.items.get("shop_items", [])
        for i, it in enumerate(items):
            box = QFrame()
            box.setStyleSheet("background: white; border: 1px solid #eee; border-radius: 10px;")
            v = QVBoxLayout(box)
            
            # 图片显示
            img_l = QLabel()
            path = os.path.join(RES_PATH, "food", it['img'])
            pix = QPixmap(path)
            if not pix.isNull():
                img_l.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            img_l.setAlignment(Qt.AlignCenter)
            v.addWidget(img_l)

            # 名字价格
            v.addWidget(QLabel(f"<b>{it['name']}</b>"), alignment=Qt.AlignCenter)
            v.addWidget(QLabel(f"🪙 {it['price']}"), alignment=Qt.AlignCenter)
            
            btn = QPushButton("购买")
            # 💡 依然是只传引用，点击才扣钱
            btn.clicked.connect(lambda ch, item=it: self.buy_item(item))
            v.addWidget(btn)
            
            self.grid.addWidget(box, i // 3, i % 3)

    def daily_check_in(self):
        # 💡 只有点那个按钮才会运行这里
        today = time.strftime("%Y-%m-%d")
        if self.parent.items.get("last_check_in") == today:
            QMessageBox.information(self, "提示", "今天已经领过工资啦~")
        else:
            reward = random.randint(20, 50)
            self.parent.items["gold"] += reward
            self.parent.items["last_check_in"] = today
            # 即时同步显示
            self.gold_label.setText(f"💰 我的金币: {self.parent.items['gold']}")
            # 物理保存
            DataManager.save_json("items.json", self.parent.items)
            QMessageBox.information(self, "成功", f"签到成功！获得 {reward} 金币。")

    def buy_item(self, it):
        if self.parent.items["gold"] >= it["price"]:
            # 1. 扣除金币
            self.parent.items["gold"] -= it["price"]
            
            # 2. 💡 修复点：调用统一的心情更新函数
            # 这样会自动修改 self.parent.items["mood"]，保存 json，并播放开心动画
            self.parent.update_mood(10) 
            
            # 3. 保存金币变动（update_mood 内部已经保存过一次 mood 了，这里保存 gold）
            DataManager.save_json("items.json", self.parent.items)
            
            # 4. 刷新商店顶部的金币和心情显示（防止点开不关时数值不跳）
            self.gold_label.setText(f"💰 金币: {self.parent.items['gold']}")
            new_mood = self.parent.items.get("mood", 80)
            self.mood_label.setText(f"{'😊' if new_mood>=70 else '😐'} 心情: {new_mood}")
            
            # 5. 关闭商店并进食
            self.accept()
            self.parent.eat_food(it["name"])
        else:
            QMessageBox.warning(self, "余额不足", "金币不够了，快去专注赚钱吧！")
            
            
            
class RandomEventDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.char_name = parent.config.get("char_name", "天成")
        self.call_name = parent.config.get("char_call_user", "主人")
        self.setWindowTitle(f"{self.char_name} 的奇遇记")
        self.resize(450, 350)
        self.layout = QVBoxLayout(self)
        
        self.desc_label = QLabel("正在推门出去中...")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font-size: 14px; margin: 10px;")
        self.layout.addWidget(self.desc_label)
        
        self.btn_layout = QVBoxLayout()
        self.layout.addLayout(self.btn_layout)
        
        # 存储 AI 返回的后果数据
        self.event_effects = {} # 格式: {"A": (心情值, 金币值), ...}

        self.fetch_event()

    def fetch_event(self):
        def task():
            # 1. 💡 从父窗口的 config 中抓取最全的人设数据
            c = self.parent.config
            char_name = c.get("char_name", "天成")
            char_gender = c.get("char_gender", "未知")
            call_name = c.get("char_call_user", "主人")
            char_extra = c.get("char_extra", "")
            

            # 2. 💡 重新组装包含“灵魂”的 Prompt
            prompt = (
                f"你是桌宠角色【{char_name}】的小剧场导演。请基于以下详细设定，生成一个符合其性格的随机路遇事件：\n\n"
                f"【角色设定】\n"
                f"- 名字：{char_name}\n"
                f"- 性别：{char_gender}\n"
                f"- 性别/背景/性格：{char_extra}\n"
                f"- 对用户的称呼：{call_name}\n\n"
                f"【任务要求】\n"
                f"提供三个行动分支供用户选择 A, B, C。选项作为用户对{char_name}的回应，必须包含一个提升{char_name}好感和一个降低{char_name}好感的选项。\n"
                f"数值范围：心情/好感(-5到+5)，金币(-5到+5)。\n"
                f"请严格按此格式返回，不要有任何多余文字：描述|A文字|A心情,A金币|B文字|B心情,B金币|C文字|C心情,C金币"
            )
            
            try:
                # 3. 调用 API
                h = {"Authorization": f"Bearer {c.get('api_key','')}"}
                r = requests.post(f"{c.get('api_url','')}/chat/completions", headers=h, 
                                 json={"model": c.get("model",""), "messages": [{"role": "user", "content": prompt}]}, timeout=15).json()
                
                content = r['choices'][0]['message']['content']
                # 发射信号让主线程处理 UI
                self.parent.api_signal.emit(f"EVENT_READY:{content}")
            except Exception as e:
                print(f"奇遇生成出错: {e}")
                self.parent.api_signal.emit("EVENT_ERROR:哎呀，时空乱流（网络错误），奇遇未能发生。")
        
        threading.Thread(target=task, daemon=True).start()

    def setup_buttons(self, content):
        try:
            # 格式解析: [描述, A文, A值, B文, B值, C文, C值]
            parts = content.split("|")
            if len(parts) < 7: raise ValueError("格式不正确")
            
            self.desc_label.setText(parts[0])
            
            # 按钮配置数据
            options_data = [
                {"label": parts[1], "values": parts[2]}, # A
                {"label": parts[3], "values": parts[4]}, # B
                {"label": parts[5], "values": parts[6]}  # C
            ]

            for data in options_data:
                btn = QPushButton(data["label"])
                btn.setMinimumHeight(40)
                # 解析数值 "心情,金币" -> (int, int)
                try:
                    m_val, g_val = map(int, data["values"].split(","))
                except:
                    m_val, g_val = 0, 0 # 兜底防止 AI 没按格式给数字
                
                btn.clicked.connect(lambda ch, mv=m_val, gv=g_val, txt=data["label"]: 
                                    self.finish_event(txt, mv, gv))
                self.btn_layout.addWidget(btn)
        except Exception as e:
            self.desc_label.setText(f"发生了一点意外: {e}\nAI返回内容: {content}")

    def finish_event(self, selected_text, m_delta, g_delta):
        # 1. 应用数值后果
        self.parent.update_mood(m_delta)
        self.parent.items["gold"] += g_delta
        DataManager.save_json("items.json", self.parent.items)
        
        # 💡 修改点：将事件结果补充到历史记录中，让 AI 记得这件事
        char_name = self.parent.config.get("char_name", "天成")
        user_name = self.parent.config.get("user_name", "你")
        # 构建一条系统描述类的消息
        event_log = f"*奇遇记录：{user_name}选择了“{selected_text}”，心情{'+' if m_delta>=0 else ''}{m_delta}，金币{'+' if g_delta>=0 else ''}{g_delta}*"
        
        # 存入历史记录（以 user 身份存入，作为背景事实）
        self.parent.history["log"].append({"role": "user", "content": event_log})
     
        DataManager.save_json("history.json", self.parent.history)
        
        # 2. 弹窗结果反馈
        res_msg = f"你选择了：{selected_text}\n\n"
        res_msg += f"💖 心情/好感: {'+' if m_delta>=0 else ''}{m_delta}\n"
        res_msg += f"🪙 金币: {'+' if g_delta>=0 else ''}{g_delta}"
        
        QMessageBox.information(self, "奇遇结果", res_msg)
        self.accept()
        
class MiniGameDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("娱乐中心")
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)

        # 游戏选择 Tab
        self.tabs = QTabWidget()
        
        # --- 1. 猜拳界面 ---
        self.rps_tab = QWidget()
        rps_l = QVBoxLayout(self.rps_tab)
        rps_l.addWidget(QLabel("和 TA 玩个猜拳吧！"), alignment=Qt.AlignCenter)
        
        btns_h = QHBoxLayout()
        for choice in ["石头", "剪刀", "布"]:
            btn = QPushButton(choice)
            btn.clicked.connect(lambda ch, c=choice: self.play_rps(c))
            btns_h.addWidget(btn)
        rps_l.addLayout(btns_h)
        
        # --- 2. 掷骰子界面 ---
        self.dice_tab = QWidget()
        dice_l = QVBoxLayout(self.dice_tab)
        dice_l.addWidget(QLabel("来比比谁的运气好？"), alignment=Qt.AlignCenter)
        btn_roll = QPushButton("🎲 掷骰子")
        btn_roll.setFixedHeight(40)
        btn_roll.clicked.connect(self.play_dice)
        dice_l.addWidget(btn_roll)

        self.tabs.addTab(self.rps_tab, "✌️ 猜拳")
        self.tabs.addTab(self.dice_tab, "🎲 骰子")
        layout.addWidget(self.tabs)

    def play_rps(self, user_choice):
        choices = ["石头", "剪刀", "布"]
        pet_choice = random.choice(choices)
        
        if user_choice == pet_choice:
            status, msg = "draw", f"我也是【{pet_choice}】！这叫心有灵犀吗？"
        elif (user_choice == "石头" and pet_choice == "剪刀") or \
             (user_choice == "剪刀" and pet_choice == "布") or \
             (user_choice == "布" and pet_choice == "石头"):
            status, msg = "lose", f"呜呜，你出【{user_choice}】赢了我的【{pet_choice}】..."
        else:
            status, msg = "win", f"嘿嘿！我的【{pet_choice}】赢过你啦！"
        
        # 💡 直接让小人去表演，不弹窗了
        self.parent.trigger_game_reaction(status, msg)

    def play_dice(self):
        u = random.randint(1, 6)
        p = random.randint(1, 6)
        
        info = f"你掷出 {u}，我掷出 {p}。"
        if u > p:
            # 输了时的随机语录
            lose_msgs = [f"{info}\n不公平！你肯定作弊了！", f"{info}\n下次我绝对会掷出6点的！",f"{info}\n哼，你运气真好，算你赢了！"]
            self.parent.trigger_game_reaction("lose", random.choice(lose_msgs))
        elif u < p:
            win_msgs = [f"{info}\n哈哈！我掷得更高，我赢了！", f"{info}\n嘿嘿，下次一定让着你！",f"{info}\n赢了有奖励吗？"]
            self.parent.trigger_game_reaction("win", random.choice(win_msgs))
        else:
            self.parent.trigger_game_reaction("draw", f"{info}\n竟然打平了，再来一局？")
        
# ================= 对话回溯 =================

class HistoryManager(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent; self.setWindowTitle("历史对话"); self.resize(500, 600)
        l = QVBoxLayout(self); self.tabs = QTabWidget()
        self.tab_log = QWidget(); log_l = QVBoxLayout(self.tab_log)
        self.scroll = QScrollArea(); self.list_w = QWidget(); self.list_l = QVBoxLayout(self.list_w)
        self.list_l.setSpacing(2); self.refresh(); self.scroll.setWidget(self.list_w); self.scroll.setWidgetResizable(True)
        log_l.addWidget(self.scroll)
        btn_r = QHBoxLayout(); b_in = QPushButton("导入"); b_ex = QPushButton("导出"); b_cl = QPushButton("全清")
        b_in.clicked.connect(self.import_h); b_ex.clicked.connect(self.export_h); b_cl.clicked.connect(self.clear_h)
        btn_r.addWidget(b_in); btn_r.addWidget(b_ex); btn_r.addWidget(b_cl); log_l.addLayout(btn_r)
        self.tab_mem = QWidget(); mem_l = QVBoxLayout(self.tab_mem)
        self.mem_edit = QTextEdit(); self.mem_edit.setPlainText(parent.history.get("events", ""))
        mem_l.addWidget(QLabel("长期记忆：")); mem_l.addWidget(self.mem_edit); b_sm = QPushButton("保存记忆"); b_sm.clicked.connect(self.save_m); mem_l.addWidget(b_sm)
        self.tabs.addTab(self.tab_log, "对话历史"); self.tabs.addTab(self.tab_mem, "长期记忆"); l.addWidget(self.tabs)

    def refresh(self):
        for i in reversed(range(self.list_l.count())): 
            w = self.list_l.itemAt(i).widget()
            if w: w.setParent(None)
        for idx, it in enumerate(self.parent.history["log"]):
            f = QFrame(); hl = QHBoxLayout(f); hl.setContentsMargins(5, 2, 5, 2)
            hl.addWidget(QLabel(f"<b>{'我' if it['role']=='user' else 'TA'}</b>: {it['content']}"), 1)
            bd = QPushButton("×"); bd.setFixedSize(18, 18); bd.clicked.connect(lambda c, i=idx: self.del_one(i)); hl.addWidget(bd)
            self.list_l.addWidget(f)

    def del_one(self, i): self.parent.history["log"].pop(i); DataManager.save_json("history.json", self.parent.history); self.refresh()
    def clear_h(self): self.parent.history["log"] = []; DataManager.save_json("history.json", self.parent.history); self.refresh()
    def export_h(self):
        p, _ = QFileDialog.getSaveFileName(self, "导出记录", "history.json", "JSON (*.json)")
        if p: DataManager.save_json(p, {"log": self.parent.history["log"]})
    def import_h(self):
        p, _ = QFileDialog.getOpenFileName(self, "导入记录", "", "JSON (*.json)")
        if p: d = DataManager.load_json(p, {"log":[]}); self.parent.history["log"] = d.get("log", []); self.refresh()
    def save_m(self): self.parent.history["events"] = self.mem_edit.toPlainText(); DataManager.save_json("history.json", self.parent.history)

# ================= 主窗体 =================

# ================= 2. 主窗体初始化 =================
class DesktopPet(QWidget):
    api_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        # 💡 增加这一行：默认设置为置顶状态
        self.is_on_top = True
        
        # --- 💡 定义完整的美食数据库默认值 ---
        default_items = {
            "gold": 100,
            "mood": 60,  # 💡 新增：初始心情值
            "last_check_in": "",
            "shop_items": [
                {"name": "包子", "price": 10, "img": "baozi.png"},
                {"name": "馄饨", "price": 15, "img": "huntun.png"},
                {"name": "米线", "price": 18, "img": "mixian.png"},
                {"name": "清汤面", "price": 12, "img": "noodle.png"},
                {"name": "牛肉面", "price": 25, "img": "beef_noodle.png"},
                {"name": "西瓜", "price": 10, "img": "watermelon.png"},
                {"name": "橙汁", "price": 8, "img": "orangejuice.png"},
                {"name": "柠檬水", "price": 5, "img": "lemonwater.png"},
                {"name": "奶茶", "price": 7, "img": "milktea.png"},
                {"name": "芭菲杯", "price": 15, "img": "parfait.png"}
            ]
        }

        # 使用强化的 load_json 加载
        self.items = DataManager.load_json("items.json", default_items)
        
        # 加载配置和历史（同样建议补全默认值）
        self.config = DataManager.load_json("config.json", {
            "api_url":"https://api.openai.com/v1", "api_key":"", "model":"gpt-3.5-turbo",
            "pet_size":200, "font_size":14, "dialog_bg":"#ffffff", "dialog_border":"#000000", "max_history": 10
        })
        self.history = DataManager.load_json("history.json", {"log": [], "events": ""})
        
        self.mood_value = 80 # 初始心情
        self.is_dragging = False; self.drag_pos = QPoint(); self.last_interact = time.time(); self.is_sleeping = False
        
        # 💡 必须在这里先创建好定时器对象，哪怕还没启动
        self.music_timer = QTimer()
        self.music_timer.timeout.connect(self.check_music_update)
        
        # 记录听歌状态的开关
        self.is_listening_music = False
        self.current_music = ""

        # ... 然后再初始化 UI
        
        self.init_ui()
        self.api_signal.connect(self.handle_signals)
        self.idle_timer = QTimer(); self.idle_timer.timeout.connect(self.check_idle); self.idle_timer.start(10000)
        
        # 在 __init__ 里的其他初始化代码下方添加：
        self.items = DataManager.load_json("items.json", {"gold": 0}) # 加载金币
        self.is_focusing = False
        self.focus_seconds = 0
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self.focus_tick)
        
        
        # 看书模式
        self.is_reading_book = False  # 听书模式开关
        self.last_clipboard_text = "" # 记录上次复制的内容，防止重复触发
        
        # 💡 PyQt 自带剪贴板监听，直接绑定信号
        self.clipboard = QApplication.clipboard()
        # 当剪贴板内容变化时，自动运行 check_clipboard 函数
        self.clipboard.dataChanged.connect(self.check_clipboard)


    def init_ui(self):
        # 💡 关键：使用 | 符号将多个标志位连接起来
    # Qt.FramelessWindowHint 是让你之前做的无边框效果保留
    # Qt.WindowStaysOnTopHint 是让它始终置顶
    # Qt.SubWindow 有时可以帮助在某些系统下更稳定地置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
    
        #self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(8)
        self.main_layout.addStretch(1)

        self.bubble = QTextBrowser()
        self.bubble.setReadOnly(True)
        self.bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded); self.bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 💡 关键：同时给组件本身和它的“内部视口”安装过滤器
        self.bubble.installEventFilter(self)
        self.bubble.viewport().installEventFilter(self)
        
        self.bubble.hide()
        self.main_layout.addWidget(self.bubble, alignment=Qt.AlignCenter)

        self.pet = QLabel()
        self.main_layout.addWidget(self.pet, alignment=Qt.AlignCenter)

        self.input = QLineEdit(); self.input.setPlaceholderText("聊聊吧...")
        self.input.returnPressed.connect(self.handle_chat)
        self.main_layout.addWidget(self.input)
        
        self.apply_styles()
        self.show()

        self.setWindowIcon(QIcon(os.path.join(RES_PATH, 'tiancheng.ico')))


    def apply_styles(self):
            import platform
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QFont

            # 1. 获取配置数据
            psize = self.config.get("pet_size", 200)
            fsize = self.config.get("font_size", 14)
            
            # 💡 根据系统选择最佳字体，解决 Mac 报错警告
            # Mac 用苹方 (PingFang SC)，Win 用微软雅黑 (Microsoft YaHei)
            is_mac = platform.system() == "Darwin"
            font_family = "'PingFang SC', 'STHeiti', sans-serif" if is_mac else "'Microsoft YaHei', 'SimSun', sans-serif"

            # 2. 调整组件尺寸
            self.pet.setFixedSize(psize, psize)
            self.bubble.setMaximumHeight(psize)
            self.bubble.setMinimumHeight(int(psize * 0.3))
            self.bubble.setFixedWidth(psize + 60)

            # 💡 3. 【核心修复】强制去除 Mac 阴影并重显
            if is_mac:
                # 这里的逻辑是：保持原有标志，并额外强加一个“无阴影”标志
                self.setWindowFlags(self.windowFlags() | Qt.NoDropShadowWindowHint)
                # 必须调用 show()，系统才会重新渲染窗口属性，把影子变掉
                self.show()

            # 4. 加载动画
            self.set_gif("stand.gif")

            # 5. 应用样式表 (使用动态字体变量)
            self.bubble.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {self.config.get('dialog_bg','#ffffff')}; 
                    border: 2px solid {self.config.get('dialog_border','#000000')}; 
                    border-radius: 12px; 
                    padding: 8px; 
                    font-size: {fsize}px; 
                    font-family: {font_family};
                }}
                QScrollBar:vertical {{ width: 4px; background: transparent; }}
                QScrollBar::handle:vertical {{ background: #ccc; border-radius: 2px; }}
            """)
            
            self.input.setStyleSheet(f"font-size: {fsize}px; font-family: {font_family};")
            
            # 6. 刷新布局
            self.updateGeometry()

    # 💡 深度修复：点击事件拦截
    def eventFilter(self, obj, event):
        # 捕获 MouseButtonPress 事件
        if event.type() == QEvent.MouseButtonPress:
            # 检查点击的是否是气泡或气泡的内部
            if obj == self.bubble or obj == self.bubble.viewport():
                # 如果打字机正在跑
                if hasattr(self, 'ty_timer') and self.ty_timer.isActive():
                    self.ty_timer.stop()
                    self.bubble.setText(self.full_t)
                    self.bubble.moveCursor(QTextCursor.End)
                    self.set_gif("stand.gif")
                else:
                    # 说完了，点击就隐藏
                    self.bubble.hide()
                return True # 表示事件处理完毕，不再向下传递
        return super().eventFilter(obj, event)

    def set_gif(self, n):
        p = os.path.join(RES_PATH, "emo", n)
        if os.path.exists(p):
            m = QMovie(p); m.setScaledSize(QSize(self.config.get("pet_size",200), self.config.get("pet_size",200)))
            self.pet.setMovie(m); m.start()

    def handle_chat(self):
        t = self.input.text()
        if t:
            self.input.clear(); self.last_interact = time.time(); self.is_sleeping = False
            self.bubble.setText("……"); self.bubble.show()
            self.set_gif("speak.gif"); self.call_api(t)

    def call_api(self, user_in, sys_ov=None, is_music_comment=False):
        def task():
            c = self.config
            call_name = c.get('char_call_user', '主人')
            # 获取当前心情文字
            mood_val = self.items.get("mood", 80)
            if mood_val >= 70: mood_str = "Happy (非常开心，语气热情活泼)"
            elif mood_val >= 30: mood_str = "Normal (平和稳定，正常交流)"
            else: mood_str = "Sad (低落难过，回复简短且带点小脾气)"
            
            # 💡 拼接人设：明确告诉 AI 对方的称呼
            base_sys = (f"你的名字是{c.get('char_name','天成')}，性别{c.get('char_gender','未知')}。"
                        f"你称呼对方为【{call_name}】。 \n"
                        f"详细人设：{c.get('char_extra','')} \n"
                        f"对方信息：我叫你{c.get('user_name','玩家')}，我的性别是{c.get('user_gender','未知')}，关系是{c.get('user_relation','主仆')}。"
                        f"对方补充资料：{c.get('user_extra','')} \n"
                        f"【你当前心情状态：{mood_str}】。请务必在回复中体现这种情绪。\n"
                        f"长期记忆：{self.history.get('events','')}")
            
            sys_prompt = sys_ov if sys_ov else base_sys
            
            
            if is_music_comment:
                # 听歌时，只给它人设和当前这一条指令，不带之前的聊天历史
                # 这样它就不会去模仿之前的乐评了
                msgs = [{"role": "system", "content": base_sys},
                        {"role": "user", "content": user_in}]
            else:
                # 普通聊天，依然保留历史记录
                msgs = [{"role": "system", "content": base_sys}]
                for m in self.history["log"][-int(c.get("max_history", 10)):]: 
                    msgs.append(m)
                msgs.append({"role": "user", "content": user_in})
            
            
            try:
                h = {"Authorization": f"Bearer {c.get('api_key','')}"}
                r = requests.post(f"{c.get('api_url','')}/chat/completions", headers=h, json={"model": c.get("model",""), "messages": msgs}, timeout=40).json()
                ans = r['choices'][0]['message']['content']
                # 在 call_api 内部保存历史记录的地方：
                # 💡 4. 优化历史记录逻辑
                # 如果是听歌评价，我们只保存 AI 的感想，不把“系统指令”当做用户的发言存进去
                if not is_music_comment and not user_in.startswith("*"):
                    self.history["log"].append({"role":"user","content":user_in})
                
                # AI 的回复（点评）依然保存到记忆中
                self.history["log"].append({"role":"assistant","content":ans})
                
                DataManager.save_json("history.json", self.history); self.api_signal.emit(ans)
            except: self.api_signal.emit(f"连接失败，请检查网络。")
        threading.Thread(target=task, daemon=True).start()

    def show_msg(self, t):
        self.bubble.show()
        self.full_t = t; self.curr_t = ""; self.idx = 0
        # 停止旧的计时器
        if hasattr(self, 'ty_timer'): self.ty_timer.stop()
        self.ty_timer = QTimer()
        self.ty_timer.timeout.connect(self.tick)
        self.ty_timer.start(40)

    def tick(self):
        if self.idx < len(self.full_t):
            self.curr_t += self.full_t[self.idx]; self.bubble.setText(self.curr_t)
            self.bubble.moveCursor(QTextCursor.End); self.idx += 1
        else: self.ty_timer.stop(); self.set_gif("stand.gif")

    def check_idle(self):
        if not self.is_sleeping and (time.time() - self.last_interact > 1200):
            self.is_sleeping = True
            self.set_gif("sleep.gif")
            c = self.config
            call_name = c.get('char_call_user', '主人')
            
            # 💡 这里的触发语也同步了称呼
            self.call_api(f"{call_name}很久没理我了，我要自言自语说句关心的话。", "你现在无聊得快睡着了。")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.is_dragging = True; self.drag_pos = e.globalPos() - self.frameGeometry().topLeft(); self.set_gif("up.gif")
    def mouseMoveEvent(self, e):
        if self.is_dragging: self.move(e.globalPos() - self.drag_pos)
    def mouseReleaseEvent(self, e): self.is_dragging = False; self.set_gif("stand.gif")

   # 1. 开启专注对话框
    def start_focus_mode(self):
        call_name = self.config.get('char_call_user', '主人')
        m, ok = QInputDialog.getInt(self, "专注时间", f"设定给{call_name}的专注分钟数:", 30, 1, 300)
        if ok:
            # 💡 关键：先停掉可能存在的旧计时器，防止叠加
            self.focus_timer.stop()
            
            self.is_focusing = True
            self.focus_seconds = m * 60
            self.focus_timer = QTimer(); self.focus_timer.timeout.connect(self.focus_tick); self.focus_timer.start(2000)
            self.show_msg(f"好的！我们要开始专注 {m} 分钟了，我会盯着{call_name}的！")
            
# 2. 核心监工逻辑
    def focus_tick(self):
        # 💡 动态获取称呼
        call_name = self.config.get('char_call_user', '主人')

        # --- A. 倒计时结束逻辑 (优先判断) ---
        if self.focus_seconds <= 0:
            # 💡 必须先停止计时器！
            self.focus_timer.stop() 
            self.is_focusing = False
            
            # 给自己一个“冷却期”，防止重入
            self.focus_seconds = 999999
            
            # 发放奖励
            reward = 20
            self.items["gold"] += reward
            DataManager.save_json("items.json", self.items)
            
            # 状态重置
            self.set_gif("stand.gif")
            
            # 💡 调用 API 夸奖，使用动态称呼
            prompt_ov = (f"【系统指令：{call_name}圆满完成了专注任务！请你用符合人设的口气夸奖TA，"
                         f"并提到你已经奖励了TA {reward} 金币。直接开始表演，不要复述指令。】")
            
            self.call_api(f"*开心地说* 任务完成了！", sys_ov=prompt_ov)
            return

        # --- B. 倒计时减少 ---
        self.focus_seconds -= 2
        
         # --- C. 摸鱼检测 (增加跨平台支持) ---
        bad_apps = ["steam", "bilibili", "epicgames", "video", "game"] 
        trigger_name = "" 

        try:
            if IS_WINDOWS:
                # --- Windows 逻辑 ---
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                active_window_title = win32gui.GetWindowText(hwnd)
                if active_window_title:
                    for word in bad_apps:
                        if word.lower() in active_window_title.lower():
                            trigger_name = f"窗口: {active_window_title[:15]}..."
                            break

            elif IS_MAC:
                # --- Mac 逻辑 ---
                # 💡 使用 AppKit 获取当前最前面的应用程序信息
                from AppKit import NSWorkspace
                
                # 获取当前活跃的应用
                active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
                app_name = active_app.localizedName() # 比如 "Steam", "Google Chrome"
                
                if app_name:
                    for word in bad_apps:
                        if word.lower() in app_name.lower():
                            trigger_name = f"应用: {app_name}"
                            break
                    
        except Exception as e:
            # 如果检测过程报错，只在后台打印，不干扰倒计时
            print(f"监工巡逻时遇到一点小麻烦: {e}")

        # --- D. 执行报警 ---
        if trigger_name:
            self.shake_window()
            # 💡 这里的警告也同步了你的称呼
            self.bubble.setText(f"【{call_name}偷懒警告！】\n发现：{trigger_name}\n不许摸鱼，快回去工作！")
            self.bubble.show()

    # 3. 震动效果逻辑 (优化：减少阻塞)
    def shake_window(self):
        orig_pos = self.pos()
        for i in range(6):
            # 随机小幅度偏移
            delta_x = random.randint(-4, 4)
            delta_y = random.randint(-4, 4)
            self.move(orig_pos.x() + delta_x, orig_pos.y() + delta_y)
            # 💡 强制刷新 UI，防止界面卡死
            QApplication.processEvents()
            time.sleep(0.01)
        # 回到原位
        self.move(orig_pos)
        
        
    def eat_food(self, food_name):
        # 1. 切换为进食动画
        self.set_gif("eat.gif")
        self.bubble.setText(f"正在大口吃【{food_name}】...")
        self.bubble.show()
        
        # 2. 5秒后切换回正常并调用 API
        QTimer.singleShot(5000, lambda: self.finish_eating(food_name))

    def finish_eating(self, food_name):
        self.set_gif("stand.gif")
        c = self.config
        # 💡 这里把“主人”换成了 c.get('char_call_user', '对方')
        call_name = c.get('char_call_user', '主人')
        
        prompt_override = (
            f"【系统指令：{call_name}刚刚喂给你一份{food_name}。"
            f"请你立刻根据角色设定，以第一人称表现出吃完后的感想。"
            f"注意：直接说出你的感想，不要解释。】"
        )
        
        trigger_msg = f"*吃掉了{call_name}送的 {food_name}，正满足地擦嘴巴*"
        self.call_api(trigger_msg, sys_ov=prompt_override)
        
        
    def update_mood(self, delta):
        # 记录旧的心情状态
        old_mood = self.items.get("mood", 60)
        new_mood = max(1, min(100, old_mood + delta))
        self.items["mood"] = new_mood
        DataManager.save_json("items.json", self.items)
        
        # 💡 根据心情变化播放动画
        if delta > 0:
            self.set_gif("laugh.gif")
        elif delta < 0:
            self.set_gif("sad.gif")
            
        # 6秒后恢复
        QTimer.singleShot(6000, lambda: self.set_gif("stand.gif"))
        
    #随机事件
        
    def start_random_event(self):
        name = self.config.get("char_name", "天成")
        res = QMessageBox.question(self, "出门邀请", f"确定让 '{name}' 随机出门逛一逛吗？", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.event_dialog = RandomEventDialog(self)
            self.event_dialog.show()

    # 💡 修改 api_signal 的连接函数以处理特殊信号
    def handle_signals(self, t):
        # 如果是随机事件信号
        if t.startswith("EVENT_READY:"):
            content = t.replace("EVENT_READY:", "")
            if hasattr(self, 'event_dialog') and self.event_dialog.isVisible():
                self.event_dialog.setup_buttons(content)
        
        # 如果是报错信号
        elif t.startswith("EVENT_ERROR:"):
            if hasattr(self, 'event_dialog'):
                self.event_dialog.desc_label.setText(t.split(":")[1])
        
        # 💡 核心：如果是普通文本，手动转交给 show_msg
        else:
            # 这里的 self.show_msg 依然是你的打字机播报函数
            self.show_msg(t)
        
    def trigger_game_reaction(self, status, msg):
        # 1. 设置气泡文字并展示
        self.bubble.setText(msg)
        self.bubble.show()
        
        # 2. 根据胜负决定表情
        if status == "win":
            self.set_gif("laugh.gif")
            # 💡 赢了开心久一点：5秒
            QTimer.singleShot(5000, self.reset_to_stand)
        elif status == "lose":
            self.set_gif("sad.gif")
            # 💡 输了委屈一会儿：5秒
            QTimer.singleShot(5000, self.reset_to_stand)
        else:
            # 💡 平手的话，3秒后气泡消失即可
            QTimer.singleShot(3000, self.bubble.hide)

    def reset_to_stand(self):
        self.set_gif("stand.gif")
        self.bubble.hide()    

    def toggle_stay_on_top(self):
        # 切换状态
        self.is_on_top = not getattr(self, 'is_on_top', True) 
        
        # 重新设置窗口标志
        if self.is_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            # 移除置顶标志
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        
        # 💡 注意：修改 Flags 后窗口通常会隐藏，需要重新 show
        self.show()
    
    def toggle_listen_music(self):
        #print("DEBUG: 点击了切换听歌模式...") # 调试打印
        self.is_listening_music = not self.is_listening_music
        
        if self.is_listening_music:
            #print("DEBUG: 模式已开启，正在初始化监视器...")
            # 开启模式
            if not hasattr(self, 'music_monitor'):
                self.music_monitor = MusicMonitor()
            
            # 启动定时器，每 5 秒查一次
            self.music_timer.start(5000)
            self.show_msg("开启‘一起听歌’模式，我会留意你在听什么哦~")
        else:
            #print("DEBUG: 模式已关闭")
            # 关闭模式
            self.music_timer.stop()
            self.current_music = ""
            self.show_msg("已关闭‘一起听歌’模式。")

    def check_music_update(self):
        """每隔5秒被调用一次"""
        #print("DEBUG: 定时器触发 check_music_update") # 如果刷屏太快可以注释这行
        
        # ⚠️ 绝对不能有 if not IS_WINDOWS: return 这种代码！
        
        import asyncio
        try:
            # 创建一个新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行检测
            song_info = loop.run_until_complete(self.music_monitor.get_media_info())
            loop.close()

            # 调试打印：看看每5秒到底抓到了什么
            if song_info:
                print(f"DEBUG: 抓取到的歌曲: {song_info}")
            
            # 如果抓到了歌名，且和刚才听的不一样（说明切歌了）
            if song_info and song_info != self.current_music:
                print(f"DEBUG: 发现切歌！旧: {self.current_music} -> 新: {song_info}")
                self.current_music = song_info
                self.handle_music_reaction(song_info)
            elif song_info:
                # 歌没变
                pass
                
        except Exception as e:
            print(f"ERROR: 听歌逻辑出错了: {e}")

    def handle_music_reaction(self, song_info):
        """发送给 AI 进行点评"""
        # 结合你的人设系统，让评价更符合角色性格
        styles = ["感性地", "俏皮地", "略带毒舌地", "文艺地", "非常简短地"]
        chosen_style = random.choice(styles)

        prompt = (
            f"（当前情境：你正陪着{self.config.get('char_call_user','主人')}听歌）\n"
            f"当前曲目是：【{song_info}】。\n"
            f"请以{chosen_style}口吻，针对这首歌名或歌手发表一句独一无二的点评。"
            f"要求：绝对不要重复你之前说过的套话，要体现出你作为{self.config.get('char_name','天成')}的个性。"
        )
        
        # 这里的 is_music_comment=True 很重要，配合下面的修改
        self.call_api(prompt, is_music_comment=True)
        
    def handle_reading_reaction(self, clip_text):
        """让 AI 针对复制的内容发表高见"""
        # 判断内容长度，给 AI 一点提示
        length_hint = "这是一句短语" if len(clip_text) < 20 else "这是一段很有深度的文字"
        
        prompt = (
            f"（情境：你正陪着{self.config.get('char_call_user','主人')}看书/写稿）\n"
            f"对方刚刚复制了这段内容：【{clip_text}】\n"
            f"请作为【{self.config.get('char_name','天成')}】，根据你的性格（{self.config.get('char_extra','')}），"
            f"针对这段内容（{length_hint}）发表一句简短的吐槽、感悟或鼓励。"
            f"注意：直接说话，不要复读内容，保持你的一贯人设。"
        )
        
        # 调用我们修好的 call_api，这里也可以复用 is_music_comment=True 的逻辑
        # 因为它们都是“自动触发且不需要带太厚重历史”的场景
        self.call_api(prompt, is_music_comment=True)
        
    def toggle_read_book(self):
        self.is_reading_book = not self.is_reading_book
        if self.is_reading_book:
            self.show_msg("开启‘一起看书’模式，你复制的内容我都会看哦~")
        else:
            self.show_msg("已退出‘一起看书’模式。")

    def check_clipboard(self):
        # 💡 只有开启了功能才进行后续逻辑
        if not self.is_reading_book:
            return
            
        # 获取剪贴板中的纯文本
        text = self.clipboard.text().strip()
        
        # 💡 过滤逻辑：内容不能为空，且不能跟上次一样，且长度不要太离谱（比如误粘了整本书）
        if text and text != self.last_clipboard_text:
            if 2 <= len(text) <= 500: # 只对 2 到 500 字的内容感兴趣
                self.last_clipboard_text = text
                self.handle_reading_reaction(text)
            elif len(text) > 500:
                print("DEBUG: 文本太长了，我看花眼了...")
        
    def contextMenuEvent(self, e):
        m = QMenu(self)
        # 增加置顶切换选项
        stay_top_action = m.addAction("⭕始终置顶" if not self.is_on_top else "❌取消置顶")
        stay_top_action.triggered.connect(self.toggle_stay_on_top)
        
        #💡 新增：一起听歌开关
        music_action = m.addAction("🎵 一起听歌")
        music_action.setCheckable(True) # 变成复选框样式
        music_action.setChecked(self.is_listening_music)
        music_action.triggered.connect(self.toggle_listen_music)
        
        # --- 增加【一起看书】开关 ---
        read_action = m.addAction("📚 一起看书")
        read_action.setCheckable(True)
        read_action.setChecked(self.is_reading_book)
        read_action.triggered.connect(self.toggle_read_book)
        
        m.addAction("🔗 连接与设定", lambda: UnifiedSettings(self).exec_())
        m.addAction("📜 历史管理", lambda: HistoryManager(self).exec_())
        m.addAction("🍔 喂食商店", lambda: ShopBackpackDialog(self).exec_())
        m.addAction(f"🎭 带{self.config.get('char_name','天成')}出去逛逛", self.start_random_event)
        m.addAction("🎮 陪我玩玩...", lambda: MiniGameDialog(self).exec_())
                
        m.addAction("⏱ 开始专注时钟", self.start_focus_mode)
        if self.is_focusing:
            m.addAction(f"⏳ 剩余: {self.focus_seconds//60}分", lambda: None)
        m.addAction("❌ 退出程序", QApplication.quit)
        m.exec_(self.mapToGlobal(e.pos()))

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    # 在 main 函数或者设置窗口初始化里加入

    app.setStyle(QStyleFactory.create("Fusion"))
    
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
