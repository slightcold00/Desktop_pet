# 🐾 天成 Desktop Pet (Cross-Platform)

<div align="center">
<img src="./emo/stand.gif" width="200" alt="天成预览图">


<p><b>Say hello</b></p>
</div>

---

## 🌟 项目简介 (Introduction)

**天成 (Tiancheng)** 是一款基于 **PyQt5** 开发的跨平台智慧桌面宠物。它不仅拥有可爱的动态外表，还提供了大模型接口，能够为你提供情感陪伴、摸鱼监测、以及有趣的美食养成系统。（默认名字和default人设由gemini老师激情提供）

---

## ✨ 核心功能 (Features)

* **🤖 智慧对话**：接入 OpenAI/DeepSeek 等 API，支持自定义角色设定（姓名、性别、性格及对你的称呼）。
* **🚫 摸鱼检测 (Anti-Slacking)**：专注模式下自动识别当前活动窗口标题。如果你在工作时偷偷打开 Bilibili 或 Steam，天成会跳出来提醒你哦！
* **🎶 一起听歌 (Music Monitor)**：实时感知你在 Windows 或 Mac 上播放的音乐，与你共享旋律。
* **📚 一起看书**：实时监测剪贴板的变化并且发表评论，
* **🍜 美食养成**：拥有完整的商店与背包系统。你可以通过签到赚取金币，给天成买包子、奶茶或芭菲杯，提升他的心情值。
* **🌼 随机小游戏**：通过"出门逛逛"随机触发AI小剧场，你的选择将会影响他的心情或者金币。
* **🍏 跨平台适配**：针对 Windows 和 macOS 进行了深度优化，解决了 Mac 端的透明窗口投影残留及高分辨率字体显示问题。

---

## 📂 项目结构 (Folder Structure)

```text
.
├── tiancheng.py         # 主程序入口
├── data/                # 存储 config.json 和 items.json (用户存档)
├── emo/                 # 存放天成的各种动态 GIF (人物立绘)
├── food/                # 存放美食素材图片
├── res/                 # 存放图标 (icon.icns) 及 UI 资源
├── run.sh               # Mac 端一键运行脚本
└── run.bat              # Windows端一键运行脚本

```

---

## 🛠️ 技术细节 (Technical Highlights)

* **路径自适应**：利用 `sys._MEIPASS` 实现打包后的资源自动定位。
* **Mac 渲染优化**：通过 `Qt.NoDropShadowWindowHint` 彻底消除 macOS 透明窗口的残留阴影。
* **数据持久化**：采用 JSON 格式存储用户设置与角色档案，确保“记忆”永不丢失。

---

## 💻 历史版本

* **见Release**

---
