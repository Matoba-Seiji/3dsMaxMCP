# 3dsMaxMCP

通过 MCP 控制 Autodesk 3ds Max 2023 和 2025。安装后，3ds Max 顶部会出现 **3dsMax MCP** 菜单，包含“启动服务”“停止服务”“重启服务”“查看状态”。

## 工作方式

```text
Codex 等 MCP 客户端 --stdio--> max_mcp --身份握手/TCP 127.0.0.1:50012--> 3ds Max
MayaMCP 保持独立，默认使用 127.0.0.1:50011。
```

Max 客户端会先核对监听器的 `3DSMAXMCP/1` 身份标记，**核对通过后才发送 Python 脚本**。Max 监听器也核对客户端标记；旧式 Maya 客户端即使误连 Max 端口也不会执行脚本。端口绑定发生在启动成功提示之前，端口被占用会直接报错。

## 安装

要求：Windows、3ds Max 2023 或 2025，以及用于外部 MCP 进程的 Python 3.10+。Max 内嵌 Python 不需要安装外部 `mcp` 包。

在本仓库运行：

```powershell
uv sync
uv run --no-sync python install.py
```

安装器将当前源码复制到本用户的 `%APPDATA%\Autodesk\ApplicationPlugins\3dsMaxMCP.bundle`。**重新启动 3ds Max** 后，在顶部菜单选择“3dsMax MCP > 启动服务”，然后可用“查看状态”核实状态。2023 使用旧版 `menuMan`，2025 使用 `cuiRegisterMenus`；插件清单按版本加载对应入口。

若只需手动启动，也可在 MAXScript Listener 运行：

```maxscript
fileIn @"C:\你的路径\3dsMaxMCP\startup_mcp_listener.ms"
```

手动启动的成功标志是 `[3dsMaxMCP] 已启动，监听 127.0.0.1:50012`。仅看到“启动脚本执行完毕”不代表端口已绑定。

卸载顶部菜单：

```powershell
uv run --no-sync python install.py --uninstall
```

## 配置 Codex

在用户级 `~/.codex/config.toml` 中加入（把路径改成你的仓库绝对路径；`python.exe` 来自 `uv sync` 创建的虚拟环境）：

```toml
[mcp_servers."3dsmax-mcp"]
command = "C:/你的路径/3dsMaxMCP/.venv/Scripts/python.exe"
args = ["-m", "max_mcp"]
cwd = "C:/你的路径/3dsMaxMCP"
enabled = true
```

用 `codex mcp list` 检查登记项；配置更改后新开 Codex 聊天以加载工具。请运行**本仓库**的 MCP 服务端；已发布到 PyPI 的旧版本仍使用旧端口和旧协议，不能与此监听器混用。

## 故障排查与验证

- Max 菜单的“查看状态”查询当前监听器自身状态，不通过“端口开放”猜测。
- 若“启动服务”报端口占用，检查 `Get-NetTCPConnection -LocalPort 50012` 的进程归属；不要停止或重配 MayaMCP 来绕过问题。
- 连接器若提示“不是 3dsMaxMCP”，表示目标端口被其他进程占用；连接器尚未发送 Python 脚本。
- 菜单安装包需重启 Max 才会加载；安装器不会关闭正在运行的 Max 或更改场景。

MCP 工具包含任意 Python/MAXScript 执行能力，因此监听器只绑定本机 `127.0.0.1`。身份标记用于防止误连其他 DCC，不能代替恶意客户端鉴权。

---

## 🔧 工具参考

3dsmax-mcp 提供了 **24 个工具**，覆盖 3ds Max 的常用操作。以下是完整的工具列表和说明。

### 🎬 场景管理（Scene）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `new_scene` | 新建空白场景 | — |
| `open_scene` | 打开场景文件 | `file_path`: 文件路径 |
| `save_scene` | 保存当前场景 | `file_path`: 保存路径（可选，留空则覆盖保存） |
| `get_scene_info` | 获取场景信息（对象数、文件路径等） | — |
| `get_scene_objects` | 获取场景中所有对象的列表 | — |
| `import_file` | 导入外部文件到场景 | `file_path`: 文件路径 |
| `export_file` | 导出场景到文件 | `file_path`: 导出路径 |

### 📦 对象操作（Object）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `create_object` | 创建几何体 | `object_type`: 类型（Box/Sphere/Cylinder 等）, `position`: 位置, `params`: 参数 JSON |
| `delete_object` | 删除对象 | `object_name`: 对象名称 |
| `clone_object` | 克隆对象 | `object_name`: 源对象名称 |
| `rename_object` | 重命名对象 | `object_name`: 当前名称, `new_name`: 新名称 |
| `set_object_transform` | 设置对象变换（位置/旋转/缩放） | `object_name`, `position`, `rotation`, `scale` |
| `set_object_property` | 设置对象属性 | `object_name`, `property_name`, `property_value` |
| `get_object_properties` | 获取对象的详细属性 | `object_name`: 对象名称 |
| `select_objects` | 选择对象 | `object_names`: 对象名称列表 |
| `add_modifier` | 添加修改器 | `object_name`: 对象名称, `modifier_type`: 修改器类型 |

### 🎨 材质（Material）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `create_material` | 创建材质 | `material_type`: 类型（Standard/Physical 等）, `diffuse_color`: 颜色, `params`: 参数 JSON |
| `assign_material` | 将材质分配给对象 | `object_name`: 目标对象, `material_name`: 材质名称 |

### 💡 灯光（Light）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `create_light` | 创建灯光 | `light_type`: 类型（Omni/FreeSpot/Skylight 等）, `position`, `color`, `intensity` |

### 🎞️ 动画（Animation）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `set_keyframe` | 设置关键帧 | `object_name`, `frame`, `position`, `rotation`, `scale` |
| `set_time_range` | 设置动画时间范围 | 起始帧、结束帧 |

### 🔧 通用工具（Utils）

| 工具名 | 功能 | 关键参数 |
|--------|------|----------|
| `execute_maxscript` | 执行 MAXScript 代码 | `script`: MAXScript 代码字符串 |
| `execute_python_script` | 执行 Python 脚本 | `script`: Python 代码字符串 |
| `get_max_version` | 获取 3ds Max 版本信息 | — |

---

## 💡 使用示例

### 场景搭建

```
用户：帮我创建一个简单的桌子场景。桌面是一个扁平的 Box，四条腿也是 Box。

AI 会依次调用：
  → create_object(object_type="Box", name="TableTop", position="0,0,75", params='{"length":120,"width":80,"height":5}')
  → create_object(object_type="Box", name="Leg_FL", position="-50,-30,0", params='{"length":5,"width":5,"height":75}')
  → create_object(object_type="Box", name="Leg_FR", position="50,-30,0", params='{"length":5,"width":5,"height":75}')
  → create_object(object_type="Box", name="Leg_BL", position="-50,30,0", params='{"length":5,"width":5,"height":75}')
  → create_object(object_type="Box", name="Leg_BR", position="50,30,0", params='{"length":5,"width":5,"height":75}')
```

### 材质与灯光

```
用户：给桌面创建一个木质感的棕色材质，然后在桌子上方添加一盏暖黄色的灯。

AI 会依次调用：
  → create_material(material_type="Standard", name="WoodMat", diffuse_color="139,90,43")
  → assign_material(object_name="TableTop", material_name="WoodMat")
  → create_light(light_type="Omni", name="TableLight", position="0,0,200", color="255,235,200", intensity="1.2")
```

### 关键帧动画

```
用户：让球体从位置 (0,0,0) 在 60 帧内移动到 (100,0,50)，同时旋转 360 度。

AI 会依次调用：
  → set_keyframe(object_name="Sphere001", frame="0", position="0,0,0", rotation="0,0,0")
  → set_keyframe(object_name="Sphere001", frame="60", position="100,0,50", rotation="0,0,360")
  → set_time_range(...)  // 设置播放范围为 0-60
```

### 执行自定义脚本

```
用户：把所有 Box 对象的线框颜色设为红色。

AI 会调用：
  → execute_maxscript(script="for obj in objects where classOf obj == Box do obj.wireColor = color 255 0 0")
```

---

## ❗ 常见问题

### 连接问题

<details>
<summary><b>Q: 提示"无法连接到 3ds Max"怎么办？</b></summary>

请依次检查：

1. **3ds Max 是否正在运行？** —— 必须先启动 3ds Max
2. **监听器是否实际绑定？** —— 菜单选择“查看状态”，或检查 MAXScript Listener 是否显示 `[3dsMaxMCP] 已启动，监听 127.0.0.1:50012`
3. **端口是否被占用？** —— 默认使用端口 `50012`，确保没有其他程序占用
4. **防火墙设置** —— 某些安全软件可能阻止本地 Socket 通信，请添加例外

</details>

<details>
<summary><b>Q: 执行超时怎么办？</b></summary>

主线程执行上限为 120 秒，客户端等待上限为 130 秒。如果操作需要更长时间，建议：

- 将复杂操作拆分为多个简单步骤
- 避免在 MCP 工具中执行渲染等耗时操作

</details>

### 安装问题

<details>
<summary><b>Q: uv 命令找不到怎么办？</b></summary>

`uv` 是项目依赖管理工具。安装方法：

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# 或通过 pip
pip install uv
```

</details>

<details>
<summary><b>Q: 支持哪些版本的 3ds Max？</b></summary>

菜单安装包明确支持并分别适配 **3ds Max 2023 和 2025**。其他版本尚未验证。

</details>

### 使用问题

<details>
<summary><b>Q: 可以同时控制多个 3ds Max 实例吗？</b></summary>

当前版本默认连接 `127.0.0.1:50012`，仅支持单实例。如需多实例支持，需要修改监听端口配置。

</details>

<details>
<summary><b>Q: 支持 V-Ray / Arnold 等第三方渲染器吗？</b></summary>

支持！`create_material` 和 `create_light` 工具可以创建第三方插件提供的材质和灯光类型（如 `VRayMtl`、`VRayLight`），前提是 3ds Max 中已安装对应插件。对于更复杂的操作，可以使用 `execute_maxscript` 或 `execute_python_script` 工具直接执行自定义脚本。

</details>

---

## 🏗️ 项目结构

```
3dsMaxMCP/
├── max_mcp/                        # Python 包主目录
│   ├── __init__.py                 # 包入口
│   ├── __main__.py                 # python -m max_mcp 入口
│   ├── server.py                   # MCP Server 核心实现
│   ├── OperationManager.py         # 工具注册与管理
│   ├── log.py                      # 日志管理
│   ├── connector/                  # 通信层
│   │   ├── max_connection.py       # MCP Server → 3ds Max 的 TCP 客户端
│   │   ├── max_server_listener.py  # 3ds Max 端的 TCP 监听服务
│   │   └── protocol.py             # 身份握手与消息帧协议
│   ├── ui/                         # 菜单操作入口
│   ├── max_tools/                  # 所有 MCP 工具脚本
│   │   ├── scene/                  # 场景相关工具（7个）
│   │   ├── object/                 # 对象操作工具（9个）
│   │   ├── material/               # 材质工具（2个）
│   │   ├── light/                  # 灯光工具（1个）
│   │   ├── animation/              # 动画工具（2个）
│   │   └── utils/                  # 通用工具（3个）
│   └── utils/                      # 内部工具函数
├── bundle/                          # 2023/2025 顶部菜单插件包
├── install.py                       # 用户级菜单安装器
├── startup_mcp_listener.ms          # 手动启动入口
├── pyproject.toml                  # Python 包配置
├── LICENSE                         # MIT 许可证
└── README.md                       # 本文件
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可。

本仓库基于 [317431629/3dsMaxMCP](https://github.com/317431629/3dsMaxMCP) 开发，保留原项目的许可证和 Git 历史。新增的菜单安装流程参考了 [Matoba-Seiji/MayaMCP](https://github.com/Matoba-Seiji/MayaMCP)，并为 3ds Max 2023、2025 分别适配顶部菜单与独立通信协议。
