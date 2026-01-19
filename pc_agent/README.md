# PC Agent Client - 电脑远程控制客户端

> ⚠️ **实验性功能** - 当前版本正在测试中，建议在非生产环境使用

**纯粹的执行器** - 在用户电脑上运行，接收服务端指令并执行。

通过 FRP + WebSocket 架构实现 PC 端的远程控制，支持 Windows 和 macOS 平台。

## 架构定位

PC Agent Client 是 PhoneAgent 项目的 **PC 端控制客户端**，与手机端的 Android Remote App 类似，都是纯粹的执行器。

```
┌─────────────────────────────────────────────────────────┐
│              PhoneAgent 服务端（智能大脑）                  │
│        AI 决策 + 任务规划 + 模型调用 + OCR 处理             │
└─────────────────────────────────────────────────────────┘
                    │                    │
         ┌──────────┴──────────┐  ┌─────┴──────────────┐
         │ PC Agent Client     │  │ Android Remote App │
         │ (本模块)             │  │ (手机端)            │
         │ 执行器               │  │ 执行器              │
         └─────────────────────┘  └────────────────────┘
```

**职责**:
- ✅ 暴露 HTTP API 接口
- ✅ 执行基础操作（点击/输入/截图）
- ✅ FRP 隧道连接
- ✅ WebSocket 设备注册

**不包含**:
- ❌ AI 模型调用（在服务端）
- ❌ 任务规划（在服务端）
- ❌ 决策逻辑（在服务端）
- ❌ OCR 处理（在服务端）

> 💡 **理解**: 就像手机端通过 Android Remote App 被服务端控制一样，PC 端通过 PC Agent Client 被服务端控制。所有智能决策都在服务端完成，客户端只负责执行。

## 特性

- ✅ **跨平台支持**: Windows 和 macOS
- ✅ **内网穿透**: 基于 FRP 实现远程访问
- ✅ **实时控制**: HTTP API 接口，低延迟响应
- ✅ **自动注册**: WebSocket 自动注册到服务端
- ✅ **中文输入**: 完整支持中文输入
- ✅ **可访问性树**: 获取 Windows UIA / macOS Accessibility 信息

## 使用场景

### 💼 办公自动化
- 自动填写表单、发送邮件
- 批量处理 Excel、Word 文档
- 定时任务和提醒

### 🧪 软件测试
- 自动化 UI 测试
- 回归测试
- 压力测试

### 🎮 其他场景
- 游戏辅助（仅限单机游戏）
- 数据采集
- 远程演示

## 环境要求

### Windows
- Python 3.9+
- Windows 10/11

### macOS
- Python 3.9+
- macOS 11.0+
- **需要授予 Accessibility 权限**

## 安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 下载 FRP 客户端

从 [FRP Releases](https://github.com/fatedier/frp/releases) 下载对应版本:

- Windows: `frpc.exe` → 放到 `bin/` 目录
- macOS: `frpc_darwin` → 放到 `bin/` 目录

### 3. 配置

```bash
# 复制配置文件
cp config.yaml.example config.yaml

# 编辑配置文件
# 修改服务器地址、FRP token 等
```

**⚠️ 重要：端口范围规则**

为了让服务端能正确识别设备类型，请遵循以下端口分配规则：

- **手机设备（Android Remote App）**: 6100-6199
- **PC 设备（PC Agent）**: 6200-6299

PC Agent 的 `remote_port` 配置必须在 **6200-6299** 范围内，否则会被误识别为手机设备。

示例配置（`config.yaml`）:
```yaml
frp:
  remote_port: 6200  # ✅ PC 设备端口（6200-6299）
```

### 4. macOS 额外步骤 - 授予 Accessibility 权限

1. 打开 **系统偏好设置** > **安全性与隐私** > **隐私**
2. 选择左侧的 **辅助功能**
3. 点击左下角的锁图标解锁
4. 勾选 **Terminal** 或 **Python**
5. 重启终端

## 使用

### 启动客户端

从项目根目录运行：

```bash
# 推荐方式: 使用启动脚本（会自动检查依赖和配置）
python pc_agent/start.py

# 或者直接启动客户端
python -m pc_agent.pc_agent_client
```

启动成功后，你会看到：
```
============================================================
 PC Agent 客户端启动
============================================================
[INFO] 检查依赖...
[INFO] 依赖检查通过
[INFO] 检查配置...
[INFO] 配置检查通过
[INFO] 检查 FRP 客户端...
[INFO] FRP 客户端检查通过
[INFO] 启动 PC Agent 客户端...
[INFO] PC Agent Client 启动成功
[INFO] 本地端口: 9999
[INFO] FRP 隧道: localhost:6200 -> 服务器
[INFO] WebSocket: 已连接到服务端
[INFO] 设备已注册: PC-xxx
```

> 💡 **提示**: `start.py` 脚本会自动检查依赖、配置文件和 FRP 客户端，推荐使用。

### 停止客户端

按 `Ctrl+C` 停止

### 验证运行

```bash
# 测试健康检查
curl http://localhost:9999/health

# 预期返回
{"status": "ok", "device_type": "pc"}
```

## API 接口

客户端启动后会在本地提供 HTTP API 接口 (默认端口 9999):

### 健康检查
```http
GET /health
```

### 点击
```http
POST /api/control/click
Content-Type: application/json

{
  "x": 100,
  "y": 200,
  "button": "left",
  "clicks": 1
}
```

### 输入文本
```http
POST /api/control/type
Content-Type: application/json

{
  "text": "Hello World"
}
```

### 按键
```http
POST /api/control/key
Content-Type: application/json

{
  "key": "enter",
  "modifiers": ["ctrl", "shift"]
}
```

### 截图
```http
POST /api/control/screenshot
```

返回 Base64 编码的 PNG 图片

### 获取感知信息
```http
GET /api/control/perception
```

返回可访问性树和屏幕信息

## 架构设计

```
┌─────────────────────────────────────────────────┐
│          客户端 (PC - Windows/Mac)               │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │   pc_agent_client.py (Python)            │  │
│  │                                          │  │
│  │   ┌──────────┐    ┌──────────────────┐  │  │
│  │   │   FRP    │    │  WebSocket       │  │  │
│  │   │  Client  │    │  (asyncio)       │  │  │
│  │   └──────────┘    └──────────────────┘  │  │
│  │        │                    │            │  │
│  │        │   ┌───────────────┐│            │  │
│  │        └──▶│ Control       ││            │  │
│  │            │ Server        ││            │  │
│  │            │ (HTTP API)    ││            │  │
│  │            │ localhost:9999││            │  │
│  │            └───────────────┘│            │  │
│  │                    │         │            │  │
│  │            ┌───────▼─────────▼──────┐    │  │
│  │            │  控制器                │    │  │
│  │            │  Windows: pyautogui   │    │  │
│  │            │          + pywinauto  │    │  │
│  │            │  Mac:     pyautogui   │    │  │
│  │            │          + PyObjC     │    │  │
│  │            └────────────────────────┘    │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                    │           │
                    │ FRP       │ WebSocket
                    │ 隧道      │ (wss://)
                    ▼           ▼
┌─────────────────────────────────────────────────┐
│          服务端 (PhoneAgent Server)              │
│                                                 │
│  ┌──────────────┐      ┌──────────────────┐   │
│  │  FRP Server  │      │  WebSocket       │   │
│  │  (7000端口)  │      │  Server          │   │
│  │              │      │  (设备管理)       │   │
│  └──────────────┘      └──────────────────┘   │
└─────────────────────────────────────────────────┘
```

## 故障排除

### Windows

**问题**: 无法导入 pywinauto
```bash
# 解决方案
pip install pywinauto pywin32
```

### macOS

**问题**: 无法控制鼠标键盘
```
# 解决方案
1. 检查 Accessibility 权限是否授予
2. 系统偏好设置 > 安全性与隐私 > 隐私 > 辅助功能
3. 确保 Terminal/Python 已勾选
```

**问题**: 无法导入 PyObjC
```bash
# 解决方案
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

## 开发

### 目录结构

```
pc_agent/
├── __init__.py              # 包初始化
├── pc_agent_client.py       # 主程序
├── control_server.py        # HTTP 控制服务器
├── frp_manager.py           # FRP 管理器
├── websocket_client.py      # WebSocket 客户端
├── controllers/             # 控制器
│   ├── __init__.py
│   ├── base_controller.py   # 抽象基类
│   ├── windows_controller.py # Windows 控制器
│   └── mac_controller.py    # Mac 控制器
├── bin/                     # FRP 可执行文件
├── config.yaml.example      # 配置示例
├── requirements.txt         # 依赖
└── README.md               # 文档
```

### 添加新功能

1. 在 `base_controller.py` 中定义抽象方法
2. 在 `windows_controller.py` 和 `mac_controller.py` 中实现
3. 在 `control_server.py` 中添加 API 接口

## ⚠️ 注意事项

1. **实验性功能**: 当前版本仍在测试中，可能存在未知问题
2. **权限要求**: macOS 需要授予 Accessibility 权限，Windows 无需特殊权限
3. **安全性**: 仅在可信网络环境中使用，避免暴露在公网
4. **兼容性**: 不同应用程序的可访问性树支持程度不同
5. **性能**: 复杂应用的 UI 树获取可能较慢

## 常见问题

### Q: PC Agent 和服务端的关系？
A: PC Agent 是客户端执行器，只负责执行操作。所有 AI 决策、任务规划都在服务端完成。

### Q: 如何在 Web 界面控制 PC？
A: 启动 PC Agent Client 后，它会自动注册到服务端。在 PhoneAgent Web 界面的设备列表中选择 PC 设备，然后创建任务即可。

### Q: 支持哪些操作？
A: 支持点击、输入文本、按键、截图、获取可访问性树等基础操作。复杂操作由服务端 AI 组合这些基础操作完成。

### Q: 与手机端有什么区别？
A: 架构完全相同，都是通过 FRP + WebSocket 连接到服务端。唯一区别是底层控制 API（PC 用 pyautogui/pywinauto，手机用 ADB/yadb）。

## 相关文档

- [PhoneAgent 主文档](../README.md) - 项目总体介绍
- [部署文档](../DEPLOYMENT.md) - 完整部署指南

## 致谢

本项目的 PC 控制方案参考了以下开源项目的设计思路：

- **[MobileAgent](https://github.com/X-PLUG/MobileAgent)** (MIT License)
  - 参考了 PC-Agent 的架构设计
  - 参考了 Windows UIA 和 Mac Accessibility API 的使用方式
  - 本项目为独立实现，未直接复制代码

感谢开源社区的贡献！

## 许可证

本项目采用 AGPL-3.0 许可证

---

**版本**: v2.0.0  
**更新日期**: 2026-01-18  
**状态**: 🧪 实验性
