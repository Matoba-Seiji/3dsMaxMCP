# 3dsMaxMCP

通过 MCP 在 Codex 等客户端中操作 3ds Max。支持 **Windows 上的 3ds Max 2020、2023 和 2025**；可读取场景、创建和修改对象、设置材质与动画，也可执行 MAXScript 或 Python 脚本。

## 安装

需要 [uv](https://docs.astral.sh/uv/) 和 Python 3.10 或更新版本。在仓库目录运行：

```powershell
uv sync
uv run --no-sync python install.py
```

重启 3ds Max，在顶部 **3dsMax MCP → 启动服务**。可用同一菜单的 **查看状态** 确认服务已启动。Max 2020 嵌入 Python 2.7；服务器会转换仓库内 24 个 MCP 工具脚本以及受支持的用户脚本语法。Python 3 专属语法和 API 不在转换范围内。

## 配置 Codex

在 `~/.codex/config.toml` 中加入以下配置，将两处路径改为本仓库的绝对路径：

```toml
[mcp_servers."3dsmax-mcp"]
command = "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe"
args = ["-m", "max_mcp"]
cwd = "C:/你的路径/3dsMaxMCP"
enabled = true
```

重新打开 Codex 聊天，让 MCP 工具加载。Max 默认使用本机端口 `50012`，与 [MayaMCP](https://github.com/Matoba-Seiji/MayaMCP) 的 `50011` 分开。

## 多实例（同时打开多个 3ds Max）

每个 3ds Max 进程各自运行监听器，用不同端口隔离；MCP 客户端按端口连接对应实例，互不影响：

1. 第一个 Max：菜单 **3dsMax MCP → 启动服务（实例1 · 50012）**。
2. 第二个 Max：菜单 **3dsMax MCP → 启动服务（实例2 · 50013）**。
3. 客户端为每个实例各配置一条 stdio 服务器，用 `--port` 指定端口（任何 MCP 客户端通用）：

```toml
[mcp_servers."3dsmax-1"]
command = "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe"
args = ["-m", "max_mcp", "--port", "50012"]
cwd = "C:/你的路径/3dsMaxMCP"

[mcp_servers."3dsmax-2"]
command = "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe"
args = ["-m", "max_mcp", "--port", "50013"]
cwd = "C:/你的路径/3dsMaxMCP"
```

也可以不传 `--port`，改用环境变量 `MAXMCP_PORT=50013`（默认 `50012` 不变，旧配置无需修改）。客户端条目的服务名不同，工具分别显示为 `mcp__3dsmax-1__*` / `mcp__3dsmax-2__*`；两个实例的 Python 状态完全独立，调用只会发往对应端口的 Max。

使用 `mcpServers` JSON 格式的客户端（Claude Desktop、Cursor 等）等价写法：

```json
{
  "mcpServers": {
    "3dsmax-1": {
      "command": "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe",
      "args": ["-m", "max_mcp", "--port", "50012"],
      "cwd": "C:/你的路径/3dsMaxMCP"
    },
    "3dsmax-2": {
      "command": "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe",
      "args": ["-m", "max_mcp", "--port", "50013"],
      "cwd": "C:/你的路径/3dsMaxMCP"
    }
  }
}
```


注意：菜单与 `max_mcp` 代码更新后，需要重新运行 `install.py` 并重启 3ds Max，新菜单项才会出现。

## 常见问题

- **连接失败：**确认 3ds Max 正在运行，并在 **3dsMax MCP → 查看状态** 中检查服务。若端口 `50012` 被占用，关闭占用该端口的程序后重试。
- **没有顶部菜单：**重新运行安装命令并重启 3ds Max 2020、2023 或 2025。安装器将菜单文件放在 `%APPDATA%\Autodesk\ApplicationPlugins\3dsMaxMCP.bundle`。
- **卸载菜单：**运行 `uv run --no-sync python install.py --uninstall`。

## 许可与来源

[MIT 许可证](LICENSE)。本仓库基于 [317431629/3dsMaxMCP](https://github.com/317431629/3dsMaxMCP) 开发，并参考了 [MayaMCP](https://github.com/Matoba-Seiji/MayaMCP) 的菜单安装体验。
