# tiancheng_pet.py
import sys
import os
import time
import random
import threading
import requests
import asyncio
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

# === 导入我们拆分的模块 ===
from config import IS_WINDOWS, IS_MAC, RES_PATH
from data_manager import DataManager
from music_monitor import MusicMonitor
# 一次性导入所有对话框
from ui_dialogs import UnifiedSettings, ShopBackpackDialog, RandomEventDialog, MiniGameDialog, HistoryManager

# =================  主窗体 =================
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
            m = QMovie(p)
            
            # 1. 获取用户设置的大小作为“基准高度”
            # (通常桌宠是根据高度来决定大小的，宽度随身材变化)
            target_h = self.config.get("pet_size", 200)
            
            # 2. 读取 GIF 的原始尺寸
            m.jumpToFrame(0)
            orig_size = m.currentImage().size()
            
            # 3. 计算“宽高比”并得出新宽度
            if orig_size.height() > 0:
                # 比例 = 目标高度 / 原图高度
                ratio = target_h / orig_size.height()
                # 新宽度 = 原图宽度 * 比例
                new_w = int(orig_size.width() * ratio)
            else:
                # 防止除以0的兜底方案（保持正方形）
                new_w = target_h
            
            # 4. 设置 GIF 的缩放大小
            m.setScaledSize(QSize(new_w, target_h))
            
            # 5. 关键：同时调整存放 GIF 的 QLabel 容器的大小
            # 这样容器就会贴合图片，不会有留白或拉伸
            self.pet.setFixedSize(new_w, target_h)
            
            # ---------------------------

            self.pet.setMovie(m)
            m.start()

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
                self.music_monitor = MusicMonitor(self)
            
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
