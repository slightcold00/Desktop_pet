# 🐾 天成 Desktop Pet (Cross-Platform)

<div align="center">
<img src="./emo/stand.gif" width="200" alt="天成预览图">


<p><b>Say hello</b></p>
<p><i>由 Gemini 老师激情提供默认人设🤫</i></p>

</div>

---

## 🌟 项目简介 (Introduction)

**天成 (Tiancheng)** 是一款基于 **PyQt5** 开发的跨平台智慧桌面宠物。它不仅拥有可爱的动态外表，通过接入大模型，它具备了实时对话、行为反馈等功能，能够为你提供情感陪伴、摸鱼监测、以及有趣的美食养成系统。

---

## ✨ 核心功能 (Features)

* **🤖 智慧对话**：接入 OpenAI/DeepSeek 等 API，支持自定义角色设定（姓名、性别、性格及对你的称呼）。
* **🚫 摸鱼检测 (Anti-Slacking)**：专注模式下自动识别当前活动窗口标题。如果你在工作时偷偷打开 Bilibili 或 Steam，天成会跳出来提醒你哦！
* **🎶 一起听歌 (Music Monitor)**：实时感知你在 Windows 或 Mac 上播放的音乐，与你共享旋律。
* **📚 一起看书**：实时监测剪贴板的变化并且发表评论，
* **🍜 美食养成**：拥有完整的商店与背包系统。你可以通过签到赚取金币，给天成买包子、奶茶或芭菲杯，提升他的心情值。
* **🌼 随机小游戏**：通过"出门逛逛"随机触发AI小剧场，你的选择将会影响他的心情或者金币。
* **🍏 跨平台适配**：针对 Windows 和 macOS 分别进行了优化。

---

## 📂 项目结构 (Folder Structure)

```text
.
├── main.py              # 主程序入口 
├── music_monitor.py     # 音乐监控模块 
├── data_manager.py      # 数据读写
├── config.py            # 全局配置与路径常量
├── ui_dialogs.py        # UI布局
├── tiancheng_pet.py     # 核心功能
├── data/                # 用户存档 (config.json, items.json)
├── emo/                 # 天成动态 GIF 立绘
├── food/                # 美食素材图片
├── icon/                # 程序图标 
├── install.bat / install.sh        # Windows/Mac 环境一键安装依赖
├── pack.bat / pack.sh              # Windows/Mac 打包脚本
└── run.sh / run.bat                # 跨平台一键运行脚本

```
---

## 🚀 快速开始 (Quick Start)

### 0. 直接下载并解压
从Releases里可直接获取封装好的应用。

**或者：** 
### 1. 克隆项目

```bash
git clone https://github.com/slightcold00/Desktop_pet.git
cd Desktop_pet

```

### 2. 环境配置 (Windows)

直接双击运行 `install.bat / install.sh`，它会自动为你创建虚拟环境并安装必要组件。

### 3. 运行天成

```bash
python main.py

```
or 直接双击运行 `run.sh / run.bat`

---

## 💻 历史版本

* **见Release**

---

## 👤 作者 (Author)

### Main Developer:
* **GitHub**: [@slightcold00](https://github.com/slightcold00)
* **Special Thanks**: 感谢 Gemini 老师在项目灵感、代码重构及图标 Bug 修复过程中的激情陪伴与指导。✨

### Collaborators:
* **GitHub**: [@yixiaoX](https://github.com/yixiaoX)

---
