# 3dsMaxMCP

通过 MCP 在 Codex 等客户端中操作 3ds Max。支持 **Windows 上的 3ds Max 2023 和 2025**；可读取场景、创建和修改对象、设置材质与动画，也可执行 MAXScript 或 Python 脚本。

## 安装

需要 [uv](https://docs.astral.sh/uv/) 和 Python 3.10 或更新版本。在仓库目录运行：

```powershell
uv sync
uv run --no-sync python install.py
```

重启 3ds Max，在顶部 **3dsMax MCP → 启动服务**。可用同一菜单的 **查看状态** 确认服务已启动。

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

## 常见问题

- **连接失败：**确认 3ds Max 正在运行，并在 **3dsMax MCP → 查看状态** 中检查服务。若端口 `50012` 被占用，关闭占用该端口的程序后重试。
- **没有顶部菜单：**重新运行安装命令并重启 3ds Max。安装器将菜单文件放在 `%APPDATA%\Autodesk\ApplicationPlugins\3dsMaxMCP.bundle`。
- **卸载菜单：**运行 `uv run --no-sync python install.py --uninstall`。

## 许可与来源

[MIT 许可证](LICENSE)。本仓库基于 [317431629/3dsMaxMCP](https://github.com/317431629/3dsMaxMCP) 开发，并参考了 [MayaMCP](https://github.com/Matoba-Seiji/MayaMCP) 的菜单安装体验。
