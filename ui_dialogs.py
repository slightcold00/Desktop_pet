# ui_dialogs.py
import os
import time
import random
import requests
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from config import RES_PATH, DATA_PATH, IS_MAC
from data_manager import DataManager

# ================= 设置中心 =================

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
        if IS_MAC:
            safe_font = QFont("Menlo", 11) # Mac 的代码字体
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
        self.font_size.setStyleSheet(f"font-family: '{safe_font.family()}'; qproperty-alignment: 'AlignCenter';")

        # --- 3. 对话记忆长度 ---
        self.max_history = QSpinBox()
        self.max_history.setLocale(QLocale(QLocale.C))
        self.max_history.setRange(1, 50)
        self.max_history.setValue(int(self.temp_config.get("max_history", 10)))
        self.max_history.setFont(safe_font)
        self.max_history.lineEdit().setFont(safe_font)
        self.max_history.setStyleSheet(f"font-family: '{safe_font.family()}'; qproperty-alignment: 'AlignCenter';")
                
        self.current_bg = self.temp_config.get("dialog_bg", "#ffffff"); self.current_border = self.temp_config.get("dialog_border", "#000000")
        btn_bg = QPushButton("选择气泡颜色"); btn_bg.clicked.connect(lambda: self.pick_color('bg'))
        btn_bd = QPushButton("选择边框颜色"); btn_bd.clicked.connect(lambda: self.pick_color('bd'))

        # --- 4.[新增] Mac 音乐客户端选择 ---
        self.music_client_combo = QComboBox()
        self.music_client_combo.addItems(["Apple Music", "Spotify"])
        # 设置当前选中的项 (从配置读取，默认 Apple Music)
        current_client = self.temp_config.get("music_client", "Apple Music")
        self.music_client_combo.setCurrentText(current_client)
        # 美化一下
        self.music_client_combo.setFont(safe_font)
        
        api_l.addRow("API URL:", self.api_url); api_l.addRow("API Key:", self.api_key)
        api_l.addRow("连通性测试:", test_layout)
        api_l.addRow("模型选择:", self.model_combo)
        api_l.addRow(QFrame())
        api_l.addRow("桌宠像素大小:", self.pet_size); api_l.addRow("全局字体大小:", self.font_size)
        api_l.addRow("对话记忆长度:", self.max_history)
        api_l.addRow("底色设置:", btn_bg); api_l.addRow("边框设置:", btn_bd)

        if IS_MAC: # 只有 Mac 显示这个选项
            api_l.addRow("音乐客户端选择 (Mac):", self.music_client_combo)

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
        
        # 1. 更新父窗口的配置字典
        self.parent.config.update({
            "api_url": self.api_url.text(), "api_key": self.api_key.text(), "model": self.model_combo.currentText(),
            "pet_size": self.pet_size.value(), "font_size": self.font_size.value(), "music_client": self.music_client_combo.currentText(),
            "max_history": self.max_history.value(),
            "dialog_bg": self.current_bg, "dialog_border": self.current_border,
            "char_name": self.c_name.text(), "char_gender": self.c_sex.text(), "char_call_user": self.c_call.text(), "char_extra": self.c_extra.toPlainText(),
            "user_name": self.u_name.text(), "user_gender": self.u_sex.text(), "user_relation": self.u_rel.text(), "user_extra": self.u_extra.toPlainText()
        })
        
        # 2. 保存到本地文件
        DataManager.save_json("config.json", self.parent.config)

        # 💡 3. 针对 Mac 的特殊清洁逻辑 (关键修复！)
        if IS_MAC:
            # 确认主窗口确实有 self.pet 这个属性
            if hasattr(self.parent, 'pet'):
                self.parent.pet.clear()      # 先擦掉旧图
                self.parent.pet.repaint()    # 强制立刻重绘空背景
            self.parent.repaint()            # 强制重绘整个主窗口

        # 4. 应用新样式并关闭
        self.parent.apply_styles()
        self.accept()
        
# ================== 商店 ==================

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
            
            # 🛠️【核心修复点】
            # 在 CSS 中强制加入 'color: black;'
            # 这样无论系统是黑是白，这个卡片永远是“白底黑字”
            box.setStyleSheet("""
                QFrame {
                    background: white; 
                    color: black; 
                    border: 1px solid #eee; 
                    border-radius: 10px;
                }
                QLabel {
                    color: black;
                }
            """)
            
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
            # 这里的 QLabel 现在会继承上面 box 设置的 color: black
            v.addWidget(QLabel(f"<b>{it['name']}</b>"), alignment=Qt.AlignCenter)
            v.addWidget(QLabel(f"🪙 {it['price']}"), alignment=Qt.AlignCenter)
            
            btn = QPushButton("购买")
            # 💡 依然是只传引用，点击才扣钱
            # 给按钮也稍微美化一下，防止在深色模式下显得突兀
            btn.setStyleSheet("color: black; border: 1px solid #ccc; border-radius: 5px; padding: 3px;")
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

# ================= 随机事件 =================    

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
        
# ================== 小游戏 ==================

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
