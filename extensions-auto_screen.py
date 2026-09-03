"""
extensions/auto_screen.py
光遇 MCP 扩展 —— 主动读屏模块

功能:
  - start_auto_read: 开启后台定时 OCR 循环，只在文本变化时返回
  - stop_auto_read: 停止后台读屏
  - get_screen_changes: 获取最近一次变化的文本

放置:  sky-pc-mcp-companion/extensions/auto_screen.py
依赖:  主服务的 read_screen 能力
"""

import time
import logging
import threading
from typing import Optional

logger = logging.getLogger("sky.ext.auto_screen")

# ============================================================
#  主动读屏管理器
# ============================================================
class AutoScreenReader:
    """
    后台定时读屏，对比前后 OCR 文本变化
    """
    
    def __init__(self, do_read_screen):
        self.read_screen = do_read_screen
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_text = ""
        self.latest_change = None
        self.interval_sec = 2.0
        self.lock = threading.Lock()

    def _extract_text(self, result):
        """兼容主服务 read_screen 返回的 OCR 字典"""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return "\n".join(
                str(item.get("text", ""))
                for item in result.get("texts", [])
                if isinstance(item, dict) and item.get("text")
            )
        return str(result or "")

    def _find_self(self, result, nickname="鑫鑫"):
        """在 OCR 结果中查找自己的备注，并返回命中的文本和坐标"""
        # 兼容主服务适配器返回的 OCR 字符串
        if isinstance(result, str):
            return [{
                "text": line,
                "confidence": 0,
                "x": 0,
                "y": 0,
            } for line in result.splitlines() if nickname in line]

        texts = result.get("texts", []) if isinstance(result, dict) else []
        hits = []
        for item in texts:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            if nickname in text:
                hits.append({
                    "text": text,
                    "confidence": item.get("confidence", 0),
                    "x": item.get("x", 0),
                    "y": item.get("y", 0),
                })
        return hits

    def identify_self(self, nickname="鑫鑫"):
        """读取当前画面，查找自己的游戏备注"""
        result = self.read_screen()
        hits = self._find_self(result, nickname)
        return {
            "success": True,
            "nickname": nickname,
            "found": bool(hits),
            "matches": hits,
            "note": "OCR 可能有误，found=true 时仍建议结合截图确认。"
        }

    def start(self, interval_sec=2.0, max_loops=None):
        """
        启动后台读屏循环
        interval_sec: 每隔多少秒读一次
        max_loops: 最多循环几次，None=无限
        """
        if self.running:
            return {"success": False, "error": "已经在运行中"}

        with self.lock:
            self.running = True
            self.interval_sec = interval_sec
            self.last_text = ""
            self.latest_change = None

        def _loop():
            loops = 0
            logger.info(f"主动读屏启动: interval={interval_sec}s, max_loops={max_loops}")
            while self.running:
                try:
                    text = self.read_screen()
                    with self.lock:
                        if text != self.last_text:
                            logger.info(f"检测到屏幕文本变化")
                            self.latest_change = {
                                "timestamp": time.time(),
                                "old_text": self.last_text,
                                "new_text": text
                            }
                            self.last_text = text
                    
                    loops += 1
                    if max_loops and loops >= max_loops:
                        logger.info(f"达到最大循环次数 {max_loops}，停止")
                        break

                    time.sleep(self.interval_sec)
                except Exception as e:
                    logger.error(f"主动读屏异常: {e}")
                    time.sleep(1)

            with self.lock:
                self.running = False
            logger.info("主动读屏已停止")

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()
        return {"success": True, "message": "主动读屏已启动"}

    def stop(self):
        """停止后台读屏"""
        with self.lock:
            if not self.running:
                return {"success": False, "error": "当前未运行"}
            self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        return {"success": True, "message": "主动读屏已停止"}

    def get_latest_change(self):
        """获取最近一次文本变化"""
        with self.lock:
            if not self.latest_change:
                return {"has_change": False}
            
            change = self.latest_change.copy()
            self.latest_change = None  # 读取后清空
            return {
                "has_change": True,
                "timestamp": change["timestamp"],
                "old_text": change["old_text"][:500],  # 截断避免太长
                "new_text": change["new_text"][:500]
            }

    def is_running(self):
        """检查是否正在运行"""
        with self.lock:
            return self.running


# ============================================================
#  对外暴露的 MCP tool 函数
# ============================================================

_reader_instance: Optional[AutoScreenReader] = None

def register_tools(server):
    """
    注册主动读屏相关 tool 到主服务
    server 需要提供:
      - server.register_tool(name, description, input_schema, handler)
      - server.read_screen() -> str
    """
    global _reader_instance

    # 创建单例读屏器
    if not _reader_instance:
        _reader_instance = AutoScreenReader(do_read_screen=server.read_screen)

    # ---- identify_self ----
    server.register_tool(
        name="identify_self",
        description="读取当前画面，通过 OCR 查找自己的游戏备注（默认：鑫鑫）",
        input_schema={
            "type": "object",
            "properties": {
                "nickname": {
                    "type": "string",
                    "description": "自己的游戏备注",
                    "default": "鑫鑫"
                }
            }
        },
        handler=lambda args: _reader_instance.identify_self(args.get("nickname", "鑫鑫"))
    )

    # ---- start_auto_read ----
    def handle_start_auto_read(args):
        interval_sec = args.get("interval_sec", 2.0)
        max_loops = args.get("max_loops", None)
        return _reader_instance.start(interval_sec=interval_sec, max_loops=max_loops)

    server.register_tool(
        name="start_auto_read",
        description="启动后台定时 OCR 读屏，只在文本变化时记录。"
                    "适合用于监控游戏界面变化、等待特定文本出现等场景",
        input_schema={
            "type": "object",
            "properties": {
                "interval_sec": {
                    "type": "number",
                    "description": "每隔多少秒读一次屏幕(默认 2.0)",
                    "default": 2.0
                },
                "max_loops": {
                    "type": "integer",
                    "description": "最多循环几次，null=无限循环",
                    "default": None
                }
            }
        },
        handler=handle_start_auto_read
    )

    # ---- stop_auto_read ----
    server.register_tool(
        name="stop_auto_read",
        description="停止后台主动读屏",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: _reader_instance.stop()
    )

    # ---- get_screen_changes ----
    server.register_tool(
        name="get_screen_changes",
        description="获取最近一次屏幕文本变化(读取后会清空)。"
                    "如果没有变化则返回 has_change=false",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: _reader_instance.get_latest_change()
    )

    # ---- auto_read_status ----
    server.register_tool(
        name="auto_read_status",
        description="检查主动读屏是否正在运行",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: {
            "is_running": _reader_instance.is_running(),
            "interval_sec": _reader_instance.interval_sec
        }
    )

    logger.info("AutoScreen extension registered: start_auto_read, stop_auto_read, get_screen_changes, auto_read_status")