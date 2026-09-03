"""
extensions/piano.py
光遇 MCP 扩展 —— 全自动弹琴模块

功能:
  - list_songs: 列出可用曲库
  - play_music: 自动导航到乐器面板 → 弹奏指定曲目
  - play_custom: 播放自定义音符序列
  - piano_status: 检查当前是否在乐器面板

放置:  sky-pc-mcp-companion/extensions/piano.py
依赖:  主服务的 press_key / read_screen / screenshot 能力
"""

import time
import logging
import re

logger = logging.getLogger("sky.ext.piano")

# ============================================================
#  音符映射 & 曲库
# ============================================================
# PC 版光遇默认键位:
#   低音: z x c v b
#   中音: k l ; n m , .
#   高音: y u i o p h j

NOTE_ALIASES = {
    # 允许用简谱风格传入, 也允许直接传键名
    "C3": "z", "D3": "x", "E3": "c", "F3": "v", "G3": "b",
    "C4": "k", "D4": "l", "E4": ";", "F4": "n", "G4": "m", "A4": ",", "B4": ".",
    "C5": "y", "D5": "u", "E5": "i", "F5": "o", "G5": "p", "A5": "h", "B5": "j",
}

# 内置曲库  (key, duration_ms)
SONGS = {
    "小星星": [
        ("k",300),("k",300),("m",300),("m",300),(",",300),(",",300),("m",550),
        ("n",300),("n",300),(";",300),(";",300),("l",300),("l",300),("k",550),
    ],
    "生日快乐": [
        ("m",300),("m",300),(",",300),("m",300),("k",300),(".",550),
        ("m",300),("m",300),(",",300),("m",300),("l",300),("k",550),
        ("m",300),("m",300),("m",300),(";",300),("k",300),(".",300),(",",550),
        ("n",300),("n",300),(";",300),("k",300),("l",300),("k",550),
    ],
    "有我呢": [
        ("k",300),("l",300),(";",300),("m",300),(";",300),(",",300),("m",300),(";",300),("l",550),
        ("k",300),(";",300),("l",300),("k",300),("k",300),("l",550),
        ("p",300),("m",300),(";",300),(",",300),(";",300),(";",300),("l",300),("m",300),(";",300),(",",300),("l",300),(";",550),
        ("m",300),(";",300),(",",300),(";",300),(";",300),("l",300),("k",300),("l",300),(";",300),(";",300),(",",300),("k",550),
        ("k",300),("l",300),(";",300),(";",300),("m",300),("k",300),("k",300),("k",300),("l",300),(";",300),("m",300),(";",300),(".",550),
        ("m",300),(";",300),("k",300),(";",300),("l",300),("k",300),("h",300),("k",550),
    ],
    "特别的人": [
        ("i",300),("u",300),("y",300),("i",300),("i",300),("u",300),("y",300),("u",300),("p",550),
        ("p",300),("i",300),("u",300),("y",300),("u",300),("h",550),
        ("y",300),(".",300),(",",300),("m",300),("o",300),("o",300),("i",550),
        ("i",300),("i",300),("i",300),("o",300),("i",300),("u",300),("y",300),("i",550),
        ("u",300),("u",300),("u",300),("u",300),("u",300),("p",300),("y",550),
        ("u",300),("i",300),("o",300),("i",300),("y",300),(",",300),("y",550),
        ("u",300),("i",300),("o",300),("i",300),("y",300),(",",300),("y",300),("u",550),
        ("i",300),("u",300),("y",300),("i",300),("i",300),("u",300),("y",300),("u",300),("m",550),
        ("m",300),("i",300),("u",300),("y",300),("u",300),("h",550),
        ("y",300),(".",300),(",",300),("m",300),("o",300),("o",300),("i",550),
        ("i",300),("i",300),("i",300),("o",300),("i",550),
        ("i",300),("h",300),("i",300),("u",300),("i",300),("u",300),("p",550),
        ("u",300),("y",300),("u",300),("i",300),(",",300),("o",550),
        ("i",300),("u",300),("i",300),("u",300),("i",300),("h",300),("p",550),
        ("m",300),(",",300),("y",300),("u",300),("i",300),("p",300),("i",300),("u",300),("i",550),
        ("p",300),("i",300),("u",300),("i",300),("p",300),("i",300),("u",300),("i",550),
        ("p",300),("i",300),("u",300),("i",300),("y",300),("y",300),(",",300),("u",550),
        ("m",300),(",",300),("y",300),("u",300),("i",300),("h",300),("i",300),("u",300),("i",550),
        ("p",300),("i",300),("u",300),("i",300),("i",300),("o",300),("i",300),("u",300),("y",550),
        ("p",300),("i",300),("i",300),("i",300),("u",300),("y",300),(",",300),("u",550),
        ("m",300),("p",300),("i",300),("i",300),("i",300),("i",300),("u",300),("y",550),
        ("p",300),("y",300),("u",300),("y",550),
    ],
}

# ============================================================
#  界面识别 —— 根据 OCR 文本判断当前场景
# ============================================================
class ScreenState:
    UNKNOWN     = "unknown"       # 无法判断
    WORLD       = "world"         # 正常游戏世界
    MENU        = "menu"          # ESC 菜单 / 设置面板
    INSTRUMENT  = "instrument"    # 乐器面板(准备弹奏)
    CHAT        = "chat"          # 聊天框已打开
    LOADING     = "loading"       # 加载画面

# OCR 文本 → 场景  (按优先级从高到低)
# 你实际跑的时候截图看 OCR 结果, 把关键词加进来就行
SCREEN_RULES = [
    # (特征关键词列表, 场景)
    (["乐器", "钢琴", "竖琴", "吉他", "piano", "harp", "guitar"], ScreenState.INSTRUMENT),
    (["菜单", "设置", "退出", "返回", "menu", "settings"],         ScreenState.MENU),
    (["加载", "loading", "连接"],                                    ScreenState.LOADING),
    (["输入消息", "发送", "聊天", "type a message"],                  ScreenState.CHAT),
]

def detect_screen(ocr_text: str) -> str:
    """根据 OCR 文本判断当前界面状态"""
    text_lower = ocr_text.lower()
    for keywords, state in SCREEN_RULES:
        for kw in keywords:
            if kw.lower() in text_lower:
                return state
    # 如果有文字但匹配不到特征, 大概率在游戏世界里
    if len(ocr_text.strip()) > 0:
        return ScreenState.WORLD
    return ScreenState.UNKNOWN


# ============================================================
#  导航状态机: 从任意界面 → 乐器面板
# ============================================================
class PianoNavigator:
    """
    状态机导航器
    需要传入两个回调:
      - do_press_key(key, duration_ms)  调用主服务的 press_key
      - do_read_screen() -> str         调用主服务的 read_screen, 返回 OCR 文本
    """

    MAX_RETRIES = 8       # 最大导航步数(防死循环)
    STEP_WAIT   = 1.5     # 每步之间等待秒数

    def __init__(self, do_press_key, do_read_screen):
        self.press = do_press_key
        self.read  = do_read_screen

    def navigate_to_instrument(self) -> tuple[bool, str]:
        """
        自动导航到乐器面板
        返回 (成功与否, 描述信息)
        """
        for step in range(self.MAX_RETRIES):
            ocr = self.read()
            state = detect_screen(ocr)
            logger.info(f"导航 step={step} state={state}")

            if state == ScreenState.INSTRUMENT:
                return True, "已在乐器面板, 准备弹奏"

            elif state == ScreenState.MENU:
                # 在菜单里 → 按 ESC 关闭菜单回到世界
                logger.info("检测到菜单, 按 ESC 关闭")
                self.press("escape", 100)
                time.sleep(self.STEP_WAIT)

            elif state == ScreenState.CHAT:
                # 聊天框打开了 → 按 ESC 关闭
                logger.info("检测到聊天框, 按 ESC 关闭")
                self.press("escape", 100)
                time.sleep(self.STEP_WAIT)

            elif state == ScreenState.LOADING:
                # 加载中 → 等待
                logger.info("加载中, 等待...")
                time.sleep(3)

            elif state in (ScreenState.WORLD, ScreenState.UNKNOWN):
                # 在游戏世界 → 尝试打开乐器
                # 光遇 PC 版: 通常需要从表情轮盘进入乐器
                # 这里用一个可配置的按键序列
                logger.info("尝试打开乐器面板")
                self._try_open_instrument()
                time.sleep(self.STEP_WAIT)

        return False, f"导航 {self.MAX_RETRIES} 步后仍未到达乐器面板"

    def _try_open_instrument(self):
        """
        尝试从游戏世界打开乐器
        
        ---- 这里的按键序列需要根据实际 UI 调整 ----
        
        PC 版光遇打开乐器的一般路径:
          1. 按住向上箭头打开表情轮盘 (或者按特定快捷键)
          2. 移动到乐器位置
          3. 点击选择

        目前写的是一个占位序列:
          - 按 ArrowUp 打开表情轮盘
          - 等待轮盘出现
          - 按方向键选择乐器
          
        你跑起来之后截图给我看, 我来调整这个序列
        """
        # 占位: 按住 ArrowUp 约 500ms 打开表情轮盘
        self.press("up", 500)
        time.sleep(0.8)
        # 占位: 这里需要根据截图确认乐器在轮盘的哪个位置
        # 可能需要鼠标点击, 先用方向键试试
        self.press("right", 100)
        time.sleep(0.3)
        self.press("right", 100)
        time.sleep(0.3)
        self.press("return", 100)
        time.sleep(1.0)


# ============================================================
#  对外暴露的 MCP tool 函数
# ============================================================

def register_tools(server):
    """
    注册弹琴相关 tool 到主服务
    server 需要提供:
      - server.register_tool(name, description, input_schema, handler)
      - server.press_key(key, duration_ms)
      - server.read_screen() -> str
    """

    # ---- list_songs ----
    server.register_tool(
        name="list_songs",
        description="列出可用的弹琴曲库",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: {
            "songs": [
                {"name": name, "notes": len(notes)}
                for name, notes in SONGS.items()
            ]
        }
    )

    # ---- piano_status ----
    def handle_piano_status(args):
        ocr = server.read_screen()
        state = detect_screen(ocr)
        return {
            "screen_state": state,
            "is_instrument_ready": state == ScreenState.INSTRUMENT,
            "ocr_text": ocr[:500]  # 截断, 避免太长
        }

    server.register_tool(
        name="piano_status",
        description="检查当前是否在乐器面板, 返回界面状态和 OCR 文本",
        input_schema={"type": "object", "properties": {}},
        handler=handle_piano_status
    )

    # ---- play_music ----
    def handle_play_music(args):
        song_name = args.get("song_name", "小星星")
        auto_navigate = args.get("auto_navigate", True)
        tempo_scale = args.get("tempo_scale", 1.0)

        if song_name not in SONGS:
            return {
                "success": False,
                "error": f"没有这首曲子: {song_name}",
                "available": list(SONGS.keys())
            }

        # 自动导航到乐器面板
        if auto_navigate:
            nav = PianoNavigator(
                do_press_key=server.press_key,
                do_read_screen=server.read_screen
            )
            ok, msg = nav.navigate_to_instrument()
            if not ok:
                return {"success": False, "error": msg}

        # 开始弹奏
        notes = SONGS[song_name]
        logger.info(f"开始弹奏《{song_name}》, 共 {len(notes)} 个音符")

        for i, (key, ms) in enumerate(notes):
            actual_ms = int(ms * tempo_scale)
            server.press_key(key, actual_ms)
            time.sleep(0.05)  # 音符间隙

        return {
            "success": True,
            "song": song_name,
            "notes_played": len(notes),
            "tempo_scale": tempo_scale
        }

    server.register_tool(
        name="play_music",
        description="自动导航到乐器面板并弹奏指定曲目。"
                    "支持: 小星星, 生日快乐, 有我呢, 特别的人",
        input_schema={
            "type": "object",
            "properties": {
                "song_name": {
                    "type": "string",
                    "description": "曲目名称",
                    "enum": list(SONGS.keys())
                },
                "auto_navigate": {
                    "type": "boolean",
                    "description": "是否自动导航到乐器面板(默认 true)",
                    "default": True
                },
                "tempo_scale": {
                    "type": "number",
                    "description": "速度倍率, 1.0=原速, 0.8=加速, 1.5=慢速",
                    "default": 1.0
                }
            },
            "required": ["song_name"]
        },
        handler=handle_play_music
    )

    # ---- play_custom ----
    def handle_play_custom(args):
        notes = args.get("notes", [])
        auto_navigate = args.get("auto_navigate", True)

        if not notes:
            return {"success": False, "error": "notes 不能为空"}

        # 解析音符: 支持 key 名或简谱别名
        parsed = []
        for item in notes:
            if isinstance(item, list) and len(item) == 2:
                key_raw, ms = item[0], item[1]
            elif isinstance(item, dict):
                key_raw, ms = item.get("key", ""), item.get("ms", 300)
            else:
                continue
            key = NOTE_ALIASES.get(str(key_raw).upper(), str(key_raw))
            parsed.append((key, int(ms)))

        if auto_navigate:
            nav = PianoNavigator(
                do_press_key=server.press_key,
                do_read_screen=server.read_screen
            )
            ok, msg = nav.navigate_to_instrument()
            if not ok:
                return {"success": False, "error": msg}

        for key, ms in parsed:
            server.press_key(key, ms)
            time.sleep(0.05)

        return {"success": True, "notes_played": len(parsed)}

    server.register_tool(
        name="play_custom",
        description="播放自定义音符序列。每个音符格式: [key, duration_ms] 或 {key, ms}。"
                    "key 支持键名(如 k, l, ;)或简谱别名(如 C4, D5)",
        input_schema={
            "type": "object",
            "properties": {
                "notes": {
                    "type": "array",
                    "description": "音符序列",
                    "items": {
                        "type": "array",
                        "items": [
                            {"type": "string"},
                            {"type": "integer"}
                        ]
                    }
                },
                "auto_navigate": {
                    "type": "boolean",
                    "default": True
                }
            },
            "required": ["notes"]
        },
        handler=handle_play_custom
    )

    logger.info("Piano extension registered: list_songs, piano_status, play_music, play_custom")