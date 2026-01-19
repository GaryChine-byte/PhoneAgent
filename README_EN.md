<div align="center">

# 📱 PhoneAgent

### Complete AI Phone Assistant Solution, Ready to Use

**Web Interface + Backend + Terminal | One-Click Deploy | Multi-Device | Live Preview**

[![GitHub stars](https://img.shields.io/github/stars/tmwgsicp/PhoneAgent?style=for-the-badge&logo=github)](https://github.com/tmwgsicp/PhoneAgent/stargazers)
[![License](https://img.shields.io/badge/License-AGPL%203.0-blue?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)

<br>

[中文](README.md) | English

</div>

---

## 📢 Latest Updates

### 🎉 v2.0.0 - Major Update (January 2026)

#### ⚡ XML Kernel V3 (Revolutionary Performance)
- ✅ **10-20x Faster** - 1-3s/step vs 20-28s/step
- ✅ **95% Cost Reduction** - $0.01/step vs $0.15/step
- ✅ **92%+ Accuracy** - Close to Vision Kernel's 95%
- ✅ **Smart Fallback** - Auto switch to Vision Kernel on XML failure
- ✅ **Hybrid Agent** - Automatically selects optimal kernel

#### 📱 Android Remote Control App (Replaces Termux)
- ✅ **One-Click Install** - Download APK and install directly
- ✅ **80% Faster Deployment** - 5-10 minutes (was 30-60 minutes)
- ✅ **More Stable** - Built-in multi-layer keep-alive mechanisms
- ✅ **All-in-One** - FRP + ADB + yadb + WebSocket integrated

#### 🖥️ PC Agent Support
- ✅ **Windows/macOS Control** - AI can operate computers
- ✅ **Accessibility Tree** - Precise UI element recognition
- ✅ **OCR Fusion** - Text recognition + IOU algorithm optimization

#### 🔧 YADB Connection Optimization
- ✅ **Improved Stability** - Optimized cache strategy and retry mechanism
- ✅ **Smart Reconnect** - Auto detect and restore connection
- ✅ **Monitoring Tools** - Connection monitoring scripts

**📝 [View Full Details](README.md)**

---

## ✨ Why PhoneAgent?

> **Built on Open-AutoGLM, completing the last mile of engineering**

[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) is an excellent open-source phone Agent project, but only provides CLI tools. **PhoneAgent** adds Web interface, multi-device support, live preview and other capabilities, making it truly **ready to use**.

| Comparison | Open-AutoGLM | PhoneAgent |
|------------|--------------|------------|
| **Interface** | ❌ CLI only | ✅ Modern Web UI |
| **Usage** | ❌ Requires coding | ✅ Natural language + Voice |
| **Devices** | ❌ Single device | ✅ Multi-device pool |
| **Models** | ❌ Single model | ✅ GLM-4.6v series + Multi-platform |
| **Deployment** | ❌ Manual config | ✅ One-click script |
| **Preview** | ❌ None | ✅ Scrcpy live stream |
| **Protection** | ❌ None | ✅ Anti-detection system |

---

## 🎯 Project Features

### 1. Smart Execution Engine + Three Kernels ⭐

PhoneAgent uses advanced Hybrid Agent architecture with three execution kernels:

```
┌─────────────────────────────────────────────────────┐
│            PhoneAgent Smart Execution Engine         │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       XML Kernel V3 (✅ Recommended)        │    │
│  │                                              │    │
│  │  • 10-20x Faster - 1-3s/step                │    │
│  │  • 95% Cost Reduction - $0.01/step          │    │
│  │  • 92%+ Accuracy - Suitable for most apps  │    │
│  │  • UI Tree Based - Parse UIAutomator XML   │    │
│  └────────────────────────────────────────────┘    │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       Vision Kernel (Stable & Reliable)    │    │
│  │                                              │    │
│  │  • Vision Understanding - GLM-4.6v series   │    │
│  │  • 95% Accuracy - Highest precision         │    │
│  │  • Universal - Suitable for complex UI     │    │
│  │  • Complete Logs - JSONL format, traceable │    │
│  └────────────────────────────────────────────┘    │
│                                                       │
│  ┌────────────────────────────────────────────┐    │
│  │       Hybrid Agent (Smart Selection)       │    │
│  │                                              │    │
│  │  • Auto Switch - XML first, Vision fallback│    │
│  │  • Best Balance - Speed, cost and accuracy │    │
│  │  • Real-time Feedback - WebSocket progress │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Execution Kernel Selection**:
- **XML Kernel (✅ Recommended)**: Fast and cost-effective, suitable for most apps
- **Vision Kernel (Stable)**: Highest accuracy, suitable for complex UI and XML failures
- **Hybrid Agent (Smart)**: Automatically selects optimal kernel, recommended for production

### 2. Real-time Screen Preview

- Integrated Scrcpy, view device screen in real-time, <150ms latency
- H.264 video stream, efficient compression, supports remote operation
- Task execution visualization, manual takeover on errors

### 3. Multi-Device Pool Management

- Manage multiple devices simultaneously
- FRP port scanning, auto-discover online devices
- WebSocket real-time device status sync

### 4. Complete Anti-Detection System

- Time Randomization - Simulate human operation rhythm
- Coordinate Randomization - Random click position offset
- Bezier Curve Sliding - Natural sliding trajectory
- App Whitelist - Restrict operable app range

---

## 🏗️ System Architecture

PhoneAgent uses **Dual WebSocket Service** architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (Vue 3)                      │
│         https://your-domain.com or http://SERVER_IP:5173    │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────────────┬──────────────────┬───────────┐
             ↓                 ↓                  ↓           ↓
    ┌────────────────┐ ┌─────────────────┐ ┌──────────┐ ┌──────────┐
    │  API Server     │ │ WebSocket Server│ │FRP Server│ │  Device  │
    │   (Port 8000)   │ │   (Port 9999)   │ │(Port 7000)│ │(Remote)  │
    │                 │ │                 │ │          │ │          │
    │ • REST API      │ │ • Device Mgmt   │ │ • ADB Fwd│ │ • ADB Run│
    │ • Frontend WS   │ │ • Task Dispatch │ │ • Port   │ │ • Status │
    │   /api/v1/ws    │ │ • Status Sync   │ │   Tunnel │ │ • Scrcpy │
    │ • Scrcpy WS     │ │   /ws/device/*  │ │          │ │          │
    └────────────────┘ └─────────────────┘ └──────────┘ └──────────┘
```

**Three Key WebSockets**:
1. **Frontend WebSocket** (Port `8000` `/api/v1/ws`) - Real-time frontend status push
2. **Device WebSocket** (Port `9999` `/ws/device/{frp_port}`) - Device connection management
3. **Scrcpy WebSocket** (Port `8000` `/api/v1/scrcpy/stream/{device_id}`) - Video stream transmission

---

## 📸 Project Showcase

### Web Management Interface

<div align="center">
<img src="assets/images/首页.jpg" alt="Dashboard" width="800">
<p><em>Dashboard - Multi-device Management & Task Monitoring</em></p>
</div>

<div align="center">
<img src="assets/images/设备管理.jpg" alt="Device Management" width="800">
<p><em>Device Management - Real-time Multi-device Pool Status</em></p>
</div>

<div align="center">
<img src="assets/images/防风控配置.jpg" alt="Anti-Detection Config" width="800">
<p><em>Anti-Detection Config - Time Randomization & Trajectory Optimization</em></p>
</div>

<div align="center">
<img src="assets/images/性能诊断.jpg" alt="Performance Diagnostics" width="800">
<p><em>Performance Diagnostics - System Resources & Task Execution Monitoring</em></p>
</div>

### Android Voice Assistant App

> 🚧 **In Development** - iFlytek Voice Wake-up + Zhipu AI Dialogue

<div align="center">
<table>
  <tr>
    <td><img src="assets/images/app-首页.jpg" alt="App Home" width="250"></td>
    <td><img src="assets/images/app-设置1.jpg" alt="App Settings 1" width="250"></td>
    <td><img src="assets/images/app-设置2.jpg" alt="App Settings 2" width="250"></td>
    <td><img src="assets/images/app-设置3.jpg" alt="App Settings 3" width="250"></td>
  </tr>
  <tr>
    <td align="center"><em>BT-7274 Cockpit Style</em></td>
    <td align="center"><em>Model Configuration</em></td>
    <td align="center"><em>Voice Configuration</em></td>
    <td align="center"><em>Language Configuration</em></td>
  </tr>
</table>
</div>

**Positioning**: Optional voice interaction interface, works with PhoneAgent Remote

**Features**:
- 🎙️ Voice Wake-up - "Hello BT" to activate
- 💬 Streaming Recognition - Real-time speech-to-text
- 🤖 AI Dialogue - Zhipu AI large model conversation
- 🔊 TTS Playback - Voice feedback
- 📱 Task Execution - Automatic phone operations

**Design Inspiration**: Titanfall 2 BT-7274 Mech Cockpit

---

## 💡 Use Cases

### 🎯 Personal: Hands-Free

- 🚗 **Driving** - Voice messaging, navigation, music
- 🏃 **Exercise** - Control music, check messages
- 💼 **Work** - Set reminders, quick replies

### 🏢 Enterprise: Batch Automation

- **App Automated Testing** - 100 devices in parallel, 10 minutes = 2 days work
- **Content Batch Operations** - Multi-account auto-posting, anti-detection mechanism
- **Data Collection** - Automated information gathering and organization

---

## ✅ Core Features

### Tasks & Interaction

- ✅ **Natural Language Tasks** - Describe tasks in plain language, AI executes automatically
- ✅ **Voice Input** - Web voice recording + STT recognition (requires HTTPS)
- ✅ **Quick Commands** - Preset common operations, one-click execution
- ✅ **Task Interruption** - Support manual intervention and takeover
- ✅ **Smart Planning** - Pre-plan steps, batch execution (Beta)

### Device Management

- ✅ **Multi-Device Pool** - Manage 100+ devices simultaneously
- ✅ **Auto Discovery** - FRP port scanning, auto-identify online devices
- ✅ **Real-time Monitoring** - WebSocket real-time device status sync

### Live Preview

- ✅ **Scrcpy Integration** - View device screen in real-time, <150ms latency
- ✅ **H.264 Video Stream** - Efficient compression, bandwidth-saving
- ✅ **Manual Control** - Direct click to operate device

### Security & Protection

- ✅ **Time Randomization** - Simulate human operation rhythm
- ✅ **Coordinate Randomization** - Random click position offset
- ✅ **Bezier Curve Sliding** - Natural sliding trajectory
- ✅ **App Whitelist** - Restrict operable app range

---


## 🚀 Quick Start

### Requirements

**Server**:
- Ubuntu 20.04+ / Debian 11+, 2-core 4GB+
- Public IP (required for FRP tunneling)
- Open ports:
  - `7000` - FRP Server
  - `8000` - API Server (includes Frontend WS and Scrcpy WS)
  - `9999` - Device WebSocket Server
  - `6100-6199` - FRP client port range (1 port per device)

**Android Device**:
- Android 5.0+, USB debugging enabled
- Download and install PhoneAgent Remote APK (see client deployment below)

### 10-Minute Deployment

#### 1️⃣ Server

```bash
git clone https://github.com/tmwgsicp/PhoneAgent.git
cd PhoneAgent

# Configure API key
cp env.example .env
nano .env  # Fill in ZHIPU_API_KEY

# One-click install (will prompt for FRP_TOKEN during installation)
sudo bash scripts/install/install_server.sh
```

#### 2️⃣ Client (PhoneAgent Remote)

**Download and Install APK**:

1. Go to [Releases page](https://github.com/tmwgsicp/PhoneAgent/releases/latest) to download the latest version
2. Install on Android device (supports Android 5.0+)

**Configure Application**:

Open the app and fill in the following information:

| Configuration | Description | Example |
|--------------|-------------|---------|
| **Backend Server IP** | IP address of PhoneAgent server | `192.168.1.100` |
| **FRP Token** | Must match server configuration | (fill in your token) |
| **FRP Remote Port** | Unique port for each device | `6100`, `6101`, etc. |
| **WebSocket Connection Mode** | Recommended: "Direct IP Mode" | Direct IP Mode |
| **Domain Address** (Optional) | Only needed for domain proxy mode | `phoneagent.example.com` |

Click "Save and Start".

**⚠️ Important First-Time Setup** (Must execute, otherwise unable to connect):

After deployment script completes, **need to execute the following commands on your computer** to make the phone's ADB daemon listen on TCP port:

**Prerequisites**: Computer needs to have ADB tools installed first

<details>
<summary>📦 Computer ADB Installation (Click to expand)</summary>

**Windows**:
```bash
# Method 1: Use Chocolatey (Recommended)
choco install adb

# Method 2: Manual download
# Visit https://developer.android.com/tools/releases/platform-tools
# Download platform-tools, extract and add to system PATH
```

**macOS**:
```bash
# Use Homebrew
brew install android-platform-tools
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install adb
```

Verify installation:
```bash
adb version
```

</details>

**Execute ADB TCP Configuration**:

```bash
# Method 1: Execute via USB connection to computer (Recommended)
# 1. Connect phone to computer via USB
# 2. Run in computer terminal:
adb tcpip 5555

# Method 2: If phone has enabled wireless debugging (Android 11+)
# Get pairing code in phone Settings → Developer options → Wireless debugging
# Then run in computer terminal: adb pair <IP>:<port>
```

**Notes**:
- This configuration **will reset after phone reboot**, need to re-execute
- If not executed, server will show device `offline`
- Detailed usage instructions can be found in [android-remote-control/README.md](android-remote-control/README.md)

#### 3️⃣ Frontend

**Simple Mode (IP direct, 2 minutes)**:
```bash
cd web
npm install && npm run dev -- --host 0.0.0.0
# Access: http://SERVER_IP:5173
```

**Complete Mode (Domain+SSL, voice support)**: See [Deployment Guide](DEPLOYMENT.md)

### Get Zhipu AI API Key

Visit [Zhipu AI Platform](https://open.bigmodel.cn/) → Register → Create API Key → Fill in `.env`

---

## 📖 Deployment Documentation

**[📘 Deployment Guide](DEPLOYMENT.md)** - Complete deployment steps and configuration instructions

**Two Deployment Modes**:
- **Simple Mode**: IP direct, 10 minutes, suitable for quick experience and testing
- **Complete Mode**: Domain+SSL+Reverse Proxy, 30 minutes, supports voice input and full features

---

## 🤖 AI Model Support

### Default Models (Zhipu AI)

| Model | Type | Features | Recommended Scenario |
|------|------|----------|---------------------|
| `autoglm-phone` | 🆓 Free | Official Phone model, optimized for phones | **Default Recommended** ⭐ |
| `glm-4.6v-flash` | 🆓 Free | Latest vision model, high cost-performance | General vision tasks |
| `glm-4.6v` | 💰 Paid | Flagship vision model, strongest understanding | Complex tasks, high precision |
| `glm-4.6v-flashx` | 💰 Paid | Ultra-fast response version | Real-time interaction |

**Out of the Box**: Uses `autoglm-phone` by default (free, optimized for phones), no configuration needed.

**Switch to Other Models**:
```bash
# .env file
CUSTOM_MODEL_NAME=glm-4.6v-flash  # Latest free model
CUSTOM_MODEL_NAME=glm-4.6v  # Paid flagship model
CUSTOM_MODEL_NAME=glm-4.6v-flashx  # Paid ultra-fast model
```

### Multi-Platform Support

PhoneAgent supports any OpenAI-compatible vision model:

```bash
# Switch to OpenAI GPT-4o
MODEL_PROVIDER=openai
CUSTOM_API_KEY=sk-proj-xxxxx
CUSTOM_MODEL_NAME=gpt-4o

# Switch to Google Gemini
MODEL_PROVIDER=gemini
CUSTOM_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXX
CUSTOM_MODEL_NAME=gemini-2.0-flash

# Switch to Qwen
MODEL_PROVIDER=qwen
CUSTOM_API_KEY=sk-xxxxx
CUSTOM_MODEL_NAME=qwen-vl-plus
```

See configuration guide (Environment Variables Configuration section)

---

## 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Vue 3 + Vite + Element Plus + Pinia |
| **Backend** | FastAPI + SQLite + WebSocket + FRP |
| **AI** | AutoGLM-Phone / GLM-4.6v series / OpenAI-Compatible |
| **Mobile Client** | PhoneAgent Remote (Android) + ADB + Scrcpy + yadb |
| **PC Client** | pywinauto (Windows) / PyObjC (macOS) + OCR |
| **Execution Engine** | XML Kernel V3 + Vision Kernel + Hybrid Agent |

---

## 📜 License

Based on [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) (Apache 2.0) with deep refactoring, open-sourced under **AGPL 3.0**.

### Usage Scope

| Use Case | Allowed |
|----------|---------|
| ✅ Personal learning and research | Free to use |
| ✅ Internal enterprise use | Free to use |
| ✅ Modify code for internal use | Free to use |
| ⚠️ Provide modified services externally | Requires open source or commercial license |
| ⚠️ Integrate into product for sale | Requires open source or commercial license |

**AGPL 3.0 Core**: When modifying code and providing services over a network, must disclose source code.

**Commercial Licensing**: For closed-source use, please contact for commercial licensing discussion. See [LICENSE](LICENSE) file for details.

**Third-Party Licenses**: This project uses code from multiple open-source projects, see [LICENSES_THIRD_PARTY.md](LICENSES_THIRD_PARTY.md)

### ⚠️ Usage Restrictions & Responsibilities

**Please Read**: [Privacy & Security Policy](privacy_policy.txt)

PhoneAgent can control your Android device for automation. Please understand the following before use:

**Allowed Use Cases**:
- ✅ Personal device automation
- ✅ Testing and development environments
- ✅ Learning and research purposes
- ✅ Legal business process automation

**Strictly Prohibited**:
- ❌ Fake data operations (fake orders, likes, comments, etc.)
- ❌ Batch account registration, device control farms
- ❌ Violating third-party app terms of service
- ❌ Privacy invasion, account theft
- ❌ Any illegal activities

**High-Risk Operation Warnings**:
- ⚠️ Payment and transfer operations require manual review
- ⚠️ Protect sensitive information like passwords
- ⚠️ Monitor important operations manually

**Disclaimer**:
- This software is provided "as is" without warranty
- Users are fully responsible for their operations
- Developers are not liable for any losses caused by using this software
- Please comply with local laws and third-party service terms

For details, see: [privacy_policy.txt](privacy_policy.txt)

---

## 🤝 Contributing

### About Pull Requests

Due to limited personal bandwidth, currently **not accepting PRs**, but very welcome to:

- 🐛 **Submit Issues** - Report bugs, suggest features
- 💡 **Fork Project** - Freely modify and customize
- 📖 **Improvement Suggestions** - Propose documentation and feature improvements via Issues
- ⭐ **Star Support** - Give the project a Star, let more people see it

---

## 🧪 Experimental Features

<details>
<summary><b>🖥️ PC Agent - Remote PC Control (Click to expand)</b></summary>

<br>

PC Agent allows AI to control your Windows/macOS computer through the server for office automation, software testing, and more.

### Features

- ✅ **Cross-platform** - Windows and macOS
- ✅ **Accessibility Tree** - Get UI element information
- ✅ **Basic Operations** - Click, type, screenshot
- ✅ **Remote Control** - FRP tunneling + WebSocket registration

### Use Cases

- 💼 Office automation (forms, emails)
- 🧪 Software automated testing
- 🎮 Game assistance (offline only)

### Status

⚠️ **Experimental Feature** - For testing only, not recommended for production

### Documentation

See [PC Agent Full Documentation](pc_agent/README.md)

</details>

---

### Contact

<table>
  <tr>
    <td align="center">
      <img src="assets/qrcode/微信二维码.jpg" width="200"><br>
      <b>Personal WeChat</b><br>
      <em>Technical Discussion · Business Cooperation</em>
    </td>
    <td align="center">
      <img src="assets/qrcode/赞赏码.jpg" width="200"><br>
      <b>Appreciation Support</b><br>
      <em>Open Source is Hard · Thanks for Support</em>
    </td>
  </tr>
</table>

- **GitHub Issues**: [Submit Issue](https://github.com/tmwgsicp/PhoneAgent/issues)

---

## 🙏 Acknowledgments

This project is developed based on the following open-source projects, with sincere thanks.

### Core Technology Source

**[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)** (Apache 2.0)

The core execution engine of this project comes from this excellent phone Agent research project. I have made engineering transformations on top of it, adding Web interface, multi-device management, smart planning and other features.

**[Zhipu AI](https://open.bigmodel.cn/)**

Thanks for providing free autoglm-phone vision model and voice recognition services.

### Technical Infrastructure

The following open-source projects provide technical support for this project:

- **[Scrcpy](https://github.com/Genymobile/scrcpy/)** - Android screen mirroring
- **[FRP](https://github.com/fatedier/frp)** - Intranet penetration
- **[YADB](https://github.com/ysbing/YADB)** - ADB enhancement (Chinese input, forced screenshot)
- **[Vue.js](https://vuejs.org/)** - Frontend framework
- **[FastAPI](https://fastapi.tiangolo.com/)** - Backend framework
- **[Element Plus](https://element-plus.org/)** - UI component library
- **[Termux](https://termux.dev/)** - Android terminal environment (used for Remote client)

Thanks to all open-source contributors! 🙏

---

<div align="center">

**🌟 If you find this project useful, please give it a Star! 🌟**

[![Star History Chart](https://api.star-history.com/svg?repos=tmwgsicp/PhoneAgent&type=Date)](https://star-history.com/#tmwgsicp/PhoneAgent&Date)

Made with ❤️ by [tmwgsicp](https://github.com/tmwgsicp)

</div>
