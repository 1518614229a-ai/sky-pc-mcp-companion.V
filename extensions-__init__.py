"""
extensions/__init__.py
扩展模块统一加载器

用法:
  from extensions import load_extensions
  load_extensions(mcp_server)

扩展模块需要提供:
  def register_tools(server):
      # 注册工具到 server
"""

import logging
import importlib
import sys
from pathlib import Path

logger = logging.getLogger("sky.extensions")

# 可用的扩展模块列表
AVAILABLE_EXTENSIONS = [
    "piano",        # 弹琴模块
    "auto_screen",  # 主动读屏模块
]


def load_extensions(server):
    """
    加载所有可用扩展模块并注册到 MCP server
    
    参数:
      server: 主服务实例，需要提供:
        - server.controller.press_key(key, duration_ms, backend)
        - server.controller.read_screen() -> dict
        - server.register_dynamic_tool(name, description, schema, handler)
    """
    # 确保 extensions 目录在 sys.path
    ext_dir = Path(__file__).parent
    if str(ext_dir.parent) not in sys.path:
        sys.path.insert(0, str(ext_dir.parent))

    loaded_count = 0
    for ext_name in AVAILABLE_EXTENSIONS:
        try:
            logger.info(f"加载扩展: {ext_name}")
            mod = importlib.import_module(f"extensions.{ext_name}")
            
            if not hasattr(mod, "register_tools"):
                logger.warning(f"扩展 {ext_name} 没有 register_tools 函数，跳过")
                continue
            
            # 包装一个适配器，让扩展模块可以调用主服务能力
            adapter = ExtensionAdapter(server)
            mod.register_tools(adapter)
            
            loaded_count += 1
            logger.info(f"✓ 扩展 {ext_name} 加载成功")
            
        except Exception as e:
            logger.error(f"✗ 扩展 {ext_name} 加载失败: {e}", exc_info=True)
    
    logger.info(f"扩展加载完成: {loaded_count}/{len(AVAILABLE_EXTENSIONS)}")
    return loaded_count


class ExtensionAdapter:
    """
    扩展模块适配器
    把主服务的能力包装成扩展模块容易调用的接口
    """
    
    def __init__(self, mcp_server):
        self.mcp_server = mcp_server
        self._dynamic_tools = []
    
    def press_key(self, key: str, duration_ms: int = 80, backend: str = None):
        """发送按键（自动 focus）"""
        return self.mcp_server.controller.press_key(key, duration_ms, backend)
    
    def read_screen(self) -> str:
        """读屏并返回 OCR 文本"""
        result = self.mcp_server.controller.read_screen()
        # 合并所有 OCR 文本
        texts = result.get("texts", [])
        return "\n".join(t.get("text", "") for t in texts)
    
    def screenshot(self) -> str:
        """截图并返回 base64"""
        return self.mcp_server.controller.screenshot_base64()
    
    def focus_game(self):
        """聚焦游戏窗口"""
        return self.mcp_server.controller.focus_game()
    
    def register_tool(self, name: str, description: str, input_schema: dict, handler):
        """
        注册一个动态工具
        
        参数:
          name: 工具名
          description: 工具描述
          input_schema: JSON Schema (MCP inputSchema)
          handler: 处理函数 (args: dict) -> dict
        """
        self._dynamic_tools.append({
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler
        })
        
        # 注册到主服务
        self.mcp_server.register_dynamic_tool(name, description, input_schema, handler)
        logger.info(f"  → 注册工具: {name}")
    
    def get_registered_tools(self):
        """返回已注册的动态工具列表"""
        return [t["name"] for t in self._dynamic_tools]