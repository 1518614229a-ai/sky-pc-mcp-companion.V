# Sky PC MCP Companion

一个给 PC 版《Sky: Children of the Light / 光遇》用的本地 MCP 小工具。它把本机窗口截图、OCR 读屏、键盘输入和聊天输入包装成 MCP/JSON-RPC tool，方便支持 MCP 或 HTTP tool 的 AI 客户端在局域网内做陪聊和本地实验。

## 它做什么

- 识别 PC 版光遇窗口
- 截取游戏窗口并做 OCR
- 返回截图或 OCR 文本
- 发送键盘按键，例如 `w`、`space`、`f`、`q`、`enter`
- 通过剪贴板向聊天框粘贴中文/英文消息

它不读游戏内存，不修改客户端，不破解协议，也不提供刷资源、代肝或自动跑图功能。请只把它当成本地可访问性/陪聊实验使用。

## 安装

需要 Windows 和 Python 3.10 或更新版本。

```bat
git clone https://github.com/Aevella/sky-pc-mcp-companion.git
cd sky-pc-mcp-companion
python -m pip install -r requirements.txt
```

第一次启用 PaddleOCR 时可能会下载模型，等待完成即可。

## 启动 HTTP MCP

双击：

```bat
start-http.bat
```

窗口会显示类似：

```text
URL:   http://0.0.0.0:9800
Token: 一串随机 token
```

手机或其他局域网客户端连接时，不要填 `0.0.0.0`，要填电脑的局域网 IP：

```text
http://192.168.1.23:9800
```

鉴权头：

```text
Authorization: Bearer 上面显示的Token
```

电脑 IP 可以用：

```bat
ipconfig
```

找当前 Wi-Fi 或以太网下面的 `IPv4 地址`。

## 管理员模式

如果光遇、Steam、启动器或游戏平台是“以管理员身份运行”的，这个 MCP 也要用管理员权限启动。否则 Windows 可能允许截图，但不允许普通权限的 Python 给管理员权限窗口发送按键。

管理员启动方式：

1. 右键 `start-http.bat`
2. 选择“以管理员身份运行”
3. 保持弹出的命令行窗口不要关闭

如果右键 `.bat` 没有管理员选项，可以先用管理员权限打开命令提示符：

```bat
cd /d C:\path\to\sky-pc-mcp-companion
start-http.bat
```

如果 `read_screen` / `screenshot` 正常，但 `press_key` 完全不动，优先试管理员模式。

## 本地 stdio MCP

如果你的 MCP 客户端支持 stdio，可以使用：

```bat
start-stdio.bat
```

或直接配置：

```json
{
  "command": "python",
  "args": ["C:\\path\\to\\sky-pc-mcp-companion\\sky-mcp-server.py"]
}
```

## 常用 tool

### status

检查依赖、OCR、输入后端和窗口识别。

```json
{
  "name": "status",
  "arguments": {}
}
```

如果 `window` 是 `null`，说明没有找到游戏窗口。可以把游戏切到窗口化/无边框窗口化，或用真实窗口标题启动：

```bat
python sky-mcp-server.py --http --host 0.0.0.0 --port 9800 --token 你的token --window-title "窗口标题的一部分"
```

### read_screen

截图并 OCR 当前游戏窗口。

```json
{
  "name": "read_screen",
  "arguments": {}
}
```

### screenshot

返回当前游戏窗口截图。

```json
{
  "name": "screenshot",
  "arguments": {}
}
```

### press_key

发送按键。移动测试建议先用长一点的按压时间。

```json
{
  "name": "press_key",
  "arguments": {
    "key": "w",
    "duration_ms": 800,
    "backend": "pydirectinput"
  }
}
```

如果 `pydirectinput` 不动，可以试：

```json
{
  "name": "press_key",
  "arguments": {
    "key": "w",
    "duration_ms": 800,
    "backend": "pyautogui"
  }
}
```

### send_chat

打开聊天框、粘贴消息并发送。

```json
{
  "name": "send_chat",
  "arguments": {
    "message": "你好，我是本地 AI 陪聊测试",
    "backend": "pydirectinput"
  }
}
```

### type_text

如果聊天框已经手动打开，可以只粘贴文本：

```json
{
  "name": "type_text",
  "arguments": {
    "message": "测试中文输入",
    "send": true,
    "backend": "pydirectinput"
  }
}
```

## 按键没反应

如果能截图、能 OCR，但是角色不动，说明 MCP 已经连上了，问题通常在 Windows 输入层。

按顺序试：

1. 手动点一下光遇窗口内部，再测 `press_key`。
2. 把光遇切到窗口化或无边框窗口化。
3. 右键“以管理员身份运行” `start-http.bat`，尤其是光遇或 Steam 本身用管理员权限启动时。
4. 分别试 `backend: pydirectinput` 和 `backend: pyautogui`。
5. 如果截图正常但两个后端都不能动，说明这台电脑上的光遇拦截了模拟输入，需要更底层的虚拟键盘/虚拟手柄方案。

## 安全边界

- 不要把端口暴露到公网。
- 不要把 token 发给不信任的人。
- 截图和 OCR 可能包含聊天内容，不要公开上传调试日志。
- 不建议做自动刷资源、自动跑图、代肝、骚扰等用途。
- 如果游戏或平台规则不允许自动化，请停止使用。

