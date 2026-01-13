# music_monitor.py
import subprocess
from config import IS_WINDOWS, IS_MAC

# Windows 专用库导入
if IS_WINDOWS:
    try:
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
    except ImportError:
        print("Windows 媒体库未加载")

class MusicMonitor:
    def __init__(self, parent):
        self.parent = parent 
        self.last_song = ""

    async def get_media_info(self):
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
            target_app = self.parent.config.get("music_client", "Apple Music")
            print(f"DEBUG_MAC: 当前选择的音乐客户端是 {target_app}")
            # AppleScript: 强制拼接成 "Title - Artist" 字符串返回
            if target_app == "Apple Music":
                script = '''
                tell application "Music"
                    if it is running then
                        if player state is playing then
                            set t_name to name of current track
                            set t_artist to artist of current track
                            return (t_name & " - " & t_artist)
                        else
                            return "Apple Music is running but not playing"
                        end if
                    else
                        return "Apple Music app is NOT running"
                    end if
                end tell
                '''
            elif target_app == "Spotify":
                script = '''
                tell application "Spotify"
                    if it is running then
                        if player state is playing then
                            set t_name to name of current track
                            set t_artist to artist of current track
                            return (t_name & " - " & t_artist)
                        else
                            return "Spotify is running but not playing"
                        end if
                    else
                        return "Spotify app is NOT running"
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