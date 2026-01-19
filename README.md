<div align="center">

# 📱 PhoneAgent

### 开箱即用的 AI 手机助手完整解决方案

**Web 交互界面 + 后端 + 终端 | 一键部署 | 多设备管理 | 实时预览**

[![GitHub stars](https://img.shields.io/github/stars/tmwgsicp/PhoneAgent?style=for-the-badge&logo=github)](https://github.com/tmwgsicp/PhoneAgent/stargazers)
[![License](https://img.shields.io/badge/License-AGPL%203.0-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)

<br>

[中文](README.md) | [English](README_EN.md)

</div>

---

## 📢 最新更新

### 🎉 v2.0.0 - 重大更新（2026-01）

#### ⚡ XML Kernel V3（全新执行引擎）
- ✅ **速度提升 10-20 倍** - 1-3秒/步 vs 20-28秒/步
- ✅ **成本降低 95%** - $0.01/步 vs $0.15/步
- ✅ **准确率 92%+** - 接近 Vision Kernel 的 95%
- ✅ **智能降级** - XML 失败时自动切换到 Vision Kernel
- ✅ **Hybrid Agent** - 自动选择最优执行内核

#### 📱 Android Remote Control App（替代 Termux）
- ✅ **一键安装** - 下载 APK 直接安装，无需复杂配置
- ✅ **部署提速 80%** - 从 30-60 分钟缩短到 5-10 分钟
- ✅ **更稳定** - 内置多层保活机制，支持各大厂商
- ✅ **集成化** - FRP + ADB + yadb + WebSocket 一体化

#### 🖥️ PC Agent 支持
- ✅ **Windows/macOS 控制** - AI 可以操作电脑
- ✅ **可访问性树** - 精准识别 UI 元素
- ✅ **OCR 融合** - 文字识别 + IOU 算法优化

#### 🔧 YADB 连接优化
- ✅ **稳定性提升** - 优化缓存策略和重试机制
- ✅ **智能重连** - 自动检测并恢复连接
- ✅ **监控工具** - 提供连接监控脚本

---

## ✨ 为什么选择 PhoneAgent？

> **基于 Open-AutoGLM 深度重构，补齐工程化的最后一公里**

[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 是优秀的手机 Agent 开源项目，但仅提供命令行工具。**PhoneAgent** 补充了 Web 交互界面、多设备支持、实时预览等能力，让它真正**开箱即用**。

| 对比 | Open-AutoGLM | PhoneAgent |
|------|-------------|-----------|
| **界面** | ❌ 命令行 | ✅ 现代化 Web UI |
| **使用** | ❌ 需要写代码 | ✅ 自然语言 + 语音输入 |
| **设备** | ❌ 单设备 | ✅ 多设备池管理 |
| **模型** | ❌ 单一模型 | ✅ GLM-4.6v系列+多平台 |
| **部署** | ❌ 手动配置 | ✅ 一键部署脚本 |
| **预览** | ❌ 无 | ✅ Scrcpy 实时画面 |
| **防护** | ❌ 无 | ✅ 完整防风控系统 |

---

## 🎯 项目特色

### 1. 智能执行引擎 + 三种内核 ⭐

PhoneAgent 采用先进的 Hybrid Agent 架构，支持三种执行内核：

```
┌─────────────────────────────────────────────────────┐
│              PhoneAgent 智能执行引擎                  │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       XML Kernel V3（✅ 推荐）              │    │
│  │                                              │    │
│  │  • 速度快 10-20 倍 - 1-3秒/步               │    │
│  │  • 成本低 95% - $0.01/步                    │    │
│  │  • 准确率 92%+ - 适合大部分应用              │    │
│  │  • 基于 UI 树 - 解析 UIAutomator XML        │    │
│  └────────────────────────────────────────────┘    │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       Vision Kernel（稳定可靠）             │    │
│  │                                              │    │
│  │  • 视觉理解 - 基于 GLM-4.6v 系列            │    │
│  │  • 准确率 95% - 最高精度                    │    │
│  │  • 通用性强 - 适合复杂 UI                   │    │
│  │  • 完整日志 - JSONL 格式，可追溯             │    │
│  └────────────────────────────────────────────┘    │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       Hybrid Agent（智能选择）              │    │
│  │                                              │    │
│  │  • 自动切换 - XML 优先，失败时用 Vision      │    │
│  │  • 最佳平衡 - 兼顾速度、成本和准确率         │    │
│  │  • 实时反馈 - WebSocket 推送每步进度         │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**执行内核选择**:
- **XML Kernel（✅ 推荐）**: 速度快、成本低，适合大部分应用
- **Vision Kernel（稳定）**: 准确率最高，适合复杂 UI 和 XML 失败场景
- **Hybrid Agent（智能）**: 自动选择最优内核，推荐生产环境使用

### 2. 实时屏幕预览

- 集成 Scrcpy，实时查看设备屏幕，延迟 <150ms
- H.264 视频流，高效压缩，支持远程操作
- 任务执行过程可视化，出错时支持人工接管

### 3. 多设备池管理

- 支持同时管理多台设备
- FRP 端口扫描，自动发现在线设备
- WebSocket 实时同步设备状态

### 4. 完整防风控系统

- 时间随机化 - 模拟真人操作节奏
- 坐标随机化 - 点击位置随机偏移
- 贝塞尔曲线滑动 - 自然的滑动轨迹
- App 白名单 - 限制可操作的应用范围

---

## 🏗️ 系统架构

PhoneAgent 采用**双 WebSocket 服务**架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    Web 前端（Vue 3）                          │
│         https://your-domain.com 或 http://SERVER_IP:5173    │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────────────┬──────────────────┬───────────┐
             ↓                 ↓                  ↓           ↓
    ┌────────────────┐ ┌─────────────────┐ ┌──────────┐ ┌──────────┐
    │  API 服务器     │ │ WebSocket 服务器│ │FRP 服务器│ │  设备端  │
    │   (8000端口)    │ │   (9999端口)    │ │(7000端口)│ │(Remote)  │
    │                 │ │                 │ │          │ │          │
    │ • REST API      │ │ • 设备连接管理  │ │ • ADB转发│ │ • ADB执行│
    │ • 前端WS        │ │ • 任务下发      │ │ • 端口穿透│ │ • 状态上报│
    │   /api/v1/ws    │ │ • 设备状态同步  │ │          │ │ • Scrcpy │
    │ • Scrcpy WS     │ │   /ws/device/*  │ │          │ │          │
    └────────────────┘ └─────────────────┘ └──────────┘ └──────────┘
```

**三个关键 WebSocket**：
1. **前端 WebSocket** (`8000` 端口 `/api/v1/ws`) - 前端实时状态推送
2. **设备 WebSocket** (`9999` 端口 `/ws/device/{frp_port}`) - 设备连接管理
3. **Scrcpy WebSocket** (`8000` 端口 `/api/v1/scrcpy/stream/{device_id}`) - 视频流传输

---

## 📸 项目展示

### Web 管理界面

<div align="center">
<img src="assets/images/首页.jpg" alt="首页" width="800">
<p><em>首页 - 多设备管理与任务监控</em></p>
</div>

<div align="center">
<img src="assets/images/设备管理.jpg" alt="设备管理" width="800">
<p><em>设备管理 - 多设备池实时状态监控</em></p>
</div>

<div align="center">
<img src="assets/images/防风控配置.jpg" alt="防风控配置" width="800">
<p><em>防风控配置 - 时间随机化与轨迹优化</em></p>
</div>

<div align="center">
<img src="assets/images/性能诊断.jpg" alt="性能诊断" width="800">
<p><em>性能诊断 - 系统资源与任务执行监控</em></p>
</div>

### Android 语音助手 App

> 🚧 **开发中** - 基于科大讯飞语音唤醒 + 智谱AI对话

<div align="center">
<table>
  <tr>
    <td><img src="assets/images/app-首页.jpg" alt="App首页" width="250"></td>
    <td><img src="assets/images/app-设置1.jpg" alt="App设置1" width="250"></td>
    <td><img src="assets/images/app-设置2.jpg" alt="App设置2" width="250"></td>
    <td><img src="assets/images/app-设置3.jpg" alt="App设置3" width="250"></td>
  </tr>
  <tr>
    <td align="center"><em>BT-7274 驾驶舱风格</em></td>
    <td align="center"><em>模型配置</em></td>
    <td align="center"><em>语音配置</em></td>
    <td align="center"><em>语言配置</em></td>
  </tr>
</table>
</div>

**定位**：可选的语音交互入口，配合 PhoneAgent Remote 使用

**功能**：
- 🎙️ 语音唤醒 - "你好BT"唤醒系统
- 💬 流式识别 - 实时语音转文字
- 🤖 AI 对话 - 智谱AI大模型对话
- 🔊 TTS 播报 - 语音反馈
- 📱 任务执行 - 自动执行手机操作

**设计灵感**：泰坦陨落2 BT-7274 机甲驾驶舱

---

## 💡 应用场景

### 🎯 个人场景：解放双手

- 🚗 **开车时** - 语音发消息、导航、播放音乐
- 🏃 **运动时** - 控制音乐、查看消息
- 💼 **工作时** - 设置提醒、快速回复

### 🏢 企业场景：批量自动化

- **App 自动化测试** - 100 台设备并行，10 分钟完成 2 天工作量
- **内容批量运营** - 多账号自动发布，防风控机制
- **数据采集** - 自动化信息收集和整理

---

## ✅ 核心功能

### 任务与交互

- ✅ **自然语言任务** - 用中文描述任务，AI 自动执行
- ✅ **语音输入** - Web 端语音录制 + STT 识别（需 HTTPS）
- ✅ **快捷指令** - 预设常用操作，一键执行
- ✅ **任务中断** - 支持人工干预和接管
- ✅ **智能规划** - 预先规划步骤，批量执行（Beta）

### 设备管理

- ✅ **多设备池管理** - 支持同时管理 100+ 台设备
- ✅ **设备自动发现** - FRP 端口扫描，自动识别在线设备
- ✅ **状态实时监控** - WebSocket 实时同步设备状态

### 实时预览

- ✅ **Scrcpy 集成** - 实时查看设备屏幕，延迟 <150ms
- ✅ **H.264 视频流** - 高效压缩，节省带宽
- ✅ **手动控制** - 支持直接点击操作设备

### 安全与防护

- ✅ **时间随机化** - 模拟真人操作节奏
- ✅ **坐标随机化** - 点击位置随机偏移
- ✅ **贝塞尔曲线滑动** - 自然的滑动轨迹
- ✅ **App 白名单** - 限制可操作的应用范围

---

## 🚀 快速开始

### 系统要求

**服务器**：
- Ubuntu 20.04+ / Debian 11+，2核4GB+
- 公网 IP（必需，用于 FRP 穿透）
- 开放端口：
  - `7000` - FRP 服务器
  - `8000` - API 服务器（含前端 WS 和 Scrcpy WS）
  - `9999` - 设备 WebSocket 服务器
  - `6100-6199` - FRP 客户端端口范围（每台设备占用1个）

**Android 设备**：
- Android 5.0+，已开启 USB 调试
- 下载并安装 PhoneAgent Remote APK（见下方客户端部署）

### 10分钟部署

#### 1️⃣ 服务端

```bash
git clone https://github.com/tmwgsicp/PhoneAgent.git
cd PhoneAgent

# 配置 API 密钥
cp env.example .env
nano .env  # 填写 ZHIPU_API_KEY

# 一键安装（安装过程会提示输入 FRP_TOKEN）
sudo bash scripts/install/install_server.sh
```

#### 2️⃣ 客户端（PhoneAgent Remote）

**下载安装 APK**：

1. 前往 [Releases 页面](https://github.com/tmwgsicp/PhoneAgent/releases/latest) 下载最新版本 APK
2. 安装到 Android 设备（支持 Android 5.0+）

**配置应用**：

打开应用，填写以下信息：

| 配置项 | 说明 | 示例 |
|-------|------|------|
| **后端服务器 IP** | PhoneAgent 服务器的 IP 地址 | `192.168.1.100` |
| **FRP Token** | 与服务端配置保持一致 | （填写你的 token） |
| **FRP 远程端口** | 每台设备使用唯一端口 | `6100`、`6101` 等 |
| **WebSocket 连接方式** | 推荐选择"直连 IP 模式" | 直连 IP 模式 |
| **域名地址**（可选） | 仅域名代理模式需要 | `phoneagent.example.com` |

点击"保存并启动"。

**⚠️ 首次部署重要步骤**（必须执行，否则无法连接）：

安装完成后，**需要在电脑上执行以下命令**让手机的ADB守护进程监听TCP端口：

**前置要求**：电脑需要先安装 ADB 工具

<details>
<summary>📦 电脑端 ADB 安装（点击展开）</summary>

**Windows**:
```bash
# 方法1：使用 Chocolatey（推荐）
choco install adb

# 方法2：手动下载
# 访问 https://developer.android.com/tools/releases/platform-tools
# 下载 platform-tools，解压后将路径添加到系统环境变量
```

**macOS**:
```bash
# 使用 Homebrew
brew install android-platform-tools
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install adb
```

验证安装：
```bash
adb version
```

</details>

**执行 ADB TCP 配置**：

```bash
# 方法1：通过USB连接电脑执行（推荐）
# 1. 手机通过USB连接到电脑
# 2. 在电脑终端执行：
adb tcpip 5555

# 方法2：如果手机已开启无线调试（Android 11+）
# 在手机设置 → 开发者选项 → 无线调试中获取配对码
# 然后在电脑终端执行 adb pair <IP>:<端口>
```

**说明**：
- 这个配置会在**手机重启后失效**，需要重新执行
- 如果不执行此步骤，服务端会显示设备 `offline`
- 详细使用说明请查看 [android-remote-control/README.md](android-remote-control/README.md)

#### 3️⃣ 前端

**简单模式（IP 直连，2分钟）**：
```bash
cd web
npm install && npm run dev -- --host 0.0.0.0
# 访问：http://SERVER_IP:5173
```

**完整模式（域名+SSL，支持语音）**：见 [部署文档](DEPLOYMENT.md)

### 获取智谱AI密钥

访问 [智谱AI开放平台](https://open.bigmodel.cn/) → 注册 → 创建API密钥 → 填入 `.env`

---

## 📖 部署文档

**[📘 部署指南](DEPLOYMENT.md)** - 完整的部署步骤和配置说明

**两种部署模式**：
- **简单模式**：IP 直连，10分钟完成，适合快速体验和测试
- **完整模式**：域名+SSL+反向代理，30分钟完成，支持语音输入和完整功能

---

## 🤖 AI 模型支持

### 默认模型（智谱 AI）

| 模型 | 类型 | 特点 | 推荐场景 |
|------|------|------|----------|
| `autoglm-phone` | 🆓 免费 | 官方Phone模型，针对手机优化 | **默认推荐** ⭐ |
| `glm-4.6v-flash` | 🆓 免费 | 最新视觉模型，高性价比 | 通用视觉任务 |
| `glm-4.6v` | 💰 付费 | 旗舰视觉模型，最强理解 | 复杂任务、高精度 |
| `glm-4.6v-flashx` | 💰 付费 | 极速响应版本 | 实时交互 |

**开箱即用**：默认使用 `autoglm-phone`（免费，针对手机优化），无需配置。

**切换到其他模型**：
```bash
# .env 文件
CUSTOM_MODEL_NAME=glm-4.6v-flash  # 最新免费模型
CUSTOM_MODEL_NAME=glm-4.6v  # 付费旗舰模型
CUSTOM_MODEL_NAME=glm-4.6v-flashx  # 付费极速模型
```

### 多平台支持

PhoneAgent 支持任何 OpenAI 兼容的视觉模型：

```bash
# 切换到 OpenAI GPT-4o
MODEL_PROVIDER=openai
CUSTOM_API_KEY=sk-proj-xxxxx
CUSTOM_MODEL_NAME=gpt-4o

# 切换到 Google Gemini
MODEL_PROVIDER=gemini
CUSTOM_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXX
CUSTOM_MODEL_NAME=gemini-2.0-flash

# 切换到通义千问
MODEL_PROVIDER=qwen
CUSTOM_API_KEY=sk-xxxxx
CUSTOM_MODEL_NAME=qwen-vl-plus
```

详见配置指南（环境变量配置章节）

---

## 📦 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + Vite + Element Plus + Pinia |
| **后端** | FastAPI + SQLite + WebSocket + FRP |
| **AI** | AutoGLM-Phone / GLM-4.6v系列 / OpenAI-Compatible |
| **移动端客户端** | PhoneAgent Remote (Android) + ADB + Scrcpy + yadb |
| **PC 端客户端** | pywinauto (Windows) / PyObjC (macOS) + OCR |
| **执行引擎** | 逐步执行 + 智能规划（Beta）|

---

## 📜 开源协议

本项目基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)（Apache 2.0）深度重构，采用 **AGPL 3.0** 协议开源。

### 使用范围

| 使用场景 | 是否允许 |
|---------|---------|
| ✅ 个人学习和研究 | 免费使用 |
| ✅ 企业内部使用 | 免费使用 |
| ✅ 修改代码内部使用 | 免费使用 |
| ⚠️ 修改后对外提供服务 | 需开源或商业授权 |
| ⚠️ 集成到产品中销售 | 需开源或商业授权 |

**AGPL 3.0 核心**：修改代码并通过网络提供服务时，必须公开源代码。

**商业授权**：如需闭源使用，请联系洽谈商业授权。详见 [LICENSE](LICENSE) 文件。

**第三方许可证**：本项目使用了多个开源项目的代码，详见 [LICENSES_THIRD_PARTY.md](LICENSES_THIRD_PARTY.md)

### ⚠️ 使用限制与责任

**请务必阅读**：[隐私与安全政策](privacy_policy.txt)

PhoneAgent 可以控制你的 Android 设备执行自动化操作，使用前请理解以下内容：

**允许的使用场景**：
- ✅ 个人设备的自动化任务
- ✅ 测试和开发环境
- ✅ 学习和研究目的
- ✅ 合法的业务流程自动化

**严格禁止**：
- ❌ 批量刷单、刷量、刷评论等虚假数据操作
- ❌ 批量注册账号、群控设备
- ❌ 违反第三方应用服务条款的操作
- ❌ 侵犯他人隐私、盗用账号
- ❌ 任何违法违规行为

**高风险操作警告**：
- ⚠️ 涉及支付、转账的操作请人工复核
- ⚠️ 账号密码等敏感信息请妥善保护
- ⚠️ 重要操作建议手动监控执行过程

**免责声明**：
- 本软件按"原样"提供，不提供任何担保
- 使用者对自己的操作承担全部责任
- 因使用本软件导致的任何损失，开发者不承担责任
- 请遵守所在地区的法律法规和第三方服务条款

详细说明请查阅：[privacy_policy.txt](privacy_policy.txt)

---

## 🤝 参与贡献

### 关于 Pull Request

由于个人精力有限，目前**暂不接受 PR**，但非常欢迎：

- 🐛 **提交 Issue** - 报告 Bug、提出功能建议
- 💡 **Fork 项目** - 自由修改和定制
- 📖 **改进建议** - 通过 Issue 提出文档和功能改进
- ⭐ **Star 支持** - 给项目点 Star，让更多人看到

---

## 🧪 实验性功能

<details>
<summary><b>🖥️ PC Agent - 电脑远程控制（点击展开）</b></summary>

<br>

PC Agent 允许 AI 通过服务端控制你的 Windows/macOS 电脑，实现办公自动化、软件测试等场景。

### 特性

- ✅ **跨平台支持** - Windows 和 macOS
- ✅ **可访问性树** - 获取 UI 元素信息
- ✅ **基础操作** - 点击、输入、截图
- ✅ **远程控制** - FRP 穿透 + WebSocket 注册

### 使用场景

- 💼 办公自动化（填表、邮件）
- 🧪 软件自动化测试
- 🎮 游戏辅助（仅限单机）

### 状态

⚠️ **实验性功能** - 仅供测试，不建议用于生产环境

### 文档

详见 [PC Agent 完整文档](pc_agent/README.md)

</details>

---

### 联系方式

<table>
  <tr>
    <td align="center">
      <img src="assets/qrcode/微信二维码.jpg" width="200"><br>
      <b>个人微信</b><br>
      <em>技术交流 · 商务合作</em>
    </td>
    <td align="center">
      <img src="assets/qrcode/赞赏码.jpg" width="200"><br>
      <b>赞赏支持</b><br>
      <em>开源不易 · 感谢支持</em>
    </td>
  </tr>
</table>

- **GitHub Issues**: [提交问题](https://github.com/tmwgsicp/PhoneAgent/issues)

---

## 🙏 致谢

本项目基于以下开源项目开发，在此表示诚挚的感谢。

### 核心技术来源

**[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)**（Apache 2.0）

本项目的核心执行引擎来自这个优秀的手机 Agent 研究项目。我在其基础上进行了工程化改造，补充了 Web 界面、多设备管理、智能规划等功能。

**[智谱 AI](https://open.bigmodel.cn/)**

感谢提供免费的 autoglm-phone 视觉模型和语音识别服务。

### 技术基础设施

以下开源项目为本项目提供了技术支持：

- **[Scrcpy](https://github.com/Genymobile/scrcpy/)** - Android 屏幕镜像
- **[FRP](https://github.com/fatedier/frp)** - 内网穿透
- **[YADB](https://github.com/ysbing/YADB)** - ADB 增强（中文输入、强制截图）
- **[Vue.js](https://vuejs.org/)** - 前端框架
- **[FastAPI](https://fastapi.tiangolo.com/)** - 后端框架
- **[Element Plus](https://element-plus.org/)** - UI 组件库
- **[Termux](https://termux.dev/)** - Android 终端环境（用于 Remote 客户端）

感谢所有开源贡献者！🙏

---

<div align="center">

**🌟 如果觉得项目有用，请给个 Star 支持一下！🌟**

[![Star History Chart](https://api.star-history.com/svg?repos=tmwgsicp/PhoneAgent&type=Date)](https://star-history.com/#tmwgsicp/PhoneAgent&Date)

Made with ❤️ by [tmwgsicp](https://github.com/tmwgsicp)

</div>
