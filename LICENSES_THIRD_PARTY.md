# 第三方开源许可证声明

本项目使用了以下开源项目的代码或灵感，在此表示感谢。

---

## 使用的开源项目

### 1. Open-AutoGLM

- **许可证**: Apache-2.0
- **版权**: Copyright (c) 2024 ZAI Organization
- **项目地址**: https://github.com/zai-org/Open-AutoGLM
- **使用说明**: 
  - Vision 模式智能体架构基础
  - 动作处理逻辑
  - 屏幕分析和 UI 交互逻辑

---

### 2. Android Use

- **许可证**: MIT License
- **版权**: Copyright (c) 2025 languse-ai
- **项目地址**: https://github.com/languse-ai/android-use
- **使用说明**:
  - XML Kernel 架构设计思路
  - UI 树解析和元素高亮方案
  - 基于索引的精准交互机制
  - 非视觉模型支持策略

**说明**: 本项目参考了 Android Use 的 XML 解析思路，但实现为独立代码。

---

### 3. MobileAgent PC-Agent

- **许可证**: MIT License
- **版权**: Copyright (c) 2022 mPLUG (Alibaba Tongyi Lab)
- **项目地址**: https://github.com/X-PLUG/MobileAgent/tree/main/PC-Agent
- **使用说明**:
  - PC 可访问性树感知模块 (`server/pc/pc_perception.py`)
  - IOU (Intersection over Union) 计算算法
  - OCR 与可访问性树融合逻辑

**具体引用**:
- `box_iou()` 函数 - 快速向量化 IOU 计算
- `_filter_ocr_elements()` 方法 - 过滤重叠的 OCR 结果

---

### 4. YADB - ADB 功能增强工具

- **许可证**: LGPL-3.0
- **作者**: ysbing
- **项目地址**: https://github.com/ysbing/YADB
- **使用方式**: 作为独立工具调用（subprocess）
- **使用说明**:
  - 中文键盘输入支持
  - 强制截图功能（绕过应用限制）
  - 剪贴板操作
  - 高效布局 dump
  - 长按操作模拟

**注意**: 本项目通过 subprocess 调用 yadb，未修改其源码，符合 LGPL-3.0 许可证要求。

---

### 5. MAI-UI & MobileAgent (参考项目)

- **许可证**: Apache-2.0
- **版权**: MAI-UI & MobileAgent Contributors
- **项目地址**: 
  - https://github.com/X-PLUG/MobileAgent
  - https://github.com/Starlight0798/MAI-UI
- **参考内容**:
  - XML+JSON混合输出格式设计
  - 视觉语言模型交互模式
  - 动作系统架构思路

**说明**: 本项目参考了这些项目的设计思想，但未直接复制代码。

---

## 主要依赖项许可证

| 依赖项 | 许可证 | 用途 |
|--------|--------|------|
| openai | MIT | AI 模型调用 |
| fastapi | MIT | Web 框架 |
| pydantic | MIT | 数据验证 |
| Pillow | HPND | 图像处理 |
| sqlalchemy | MIT | 数据库 ORM |
| numpy | BSD-3-Clause | 数值计算 |

所有依赖项许可证均与本项目的 AGPL-3.0 许可证兼容。

---

## 致谢

感谢以下开源项目和技术为本项目提供支持：

- **Open-AutoGLM** - 视觉智能体架构
- **Android Use** - XML 内核架构思路
- **MobileAgent** - PC 控制技术
- **MAI-UI** - 输出格式设计参考
- **YADB** - ADB 增强功能
- **智谱 AI** - 中文多模态模型
- **FRP** - 内网穿透方案
- **Scrcpy** - 屏幕镜像技术
- **Vue.js / FastAPI / Element Plus** - Web 开发框架

---

## 许可证兼容性

本项目采用 **AGPL-3.0** 许可证，与以下许可证兼容：

- ✅ Apache-2.0 (Open-AutoGLM, MAI-UI)
- ✅ MIT (Android Use, MobileAgent, 大部分依赖项)
- ✅ LGPL-3.0 (YADB，通过动态链接方式)
- ✅ BSD (NumPy 等)

---

## 许可证文本

各开源项目的完整许可证文本请访问其官方仓库：

- **MIT License**: https://opensource.org/licenses/MIT
- **Apache-2.0**: https://www.apache.org/licenses/LICENSE-2.0
- **LGPL-3.0**: https://www.gnu.org/licenses/lgpl-3.0.html
- **AGPL-3.0** (本项目): https://www.gnu.org/licenses/agpl-3.0.html

---

## 联系方式

如有许可证相关问题，请通过以下方式联系：

- 项目主页: https://github.com/tmwgsicp/PhoneAgent
- Issue 追踪: https://github.com/tmwgsicp/PhoneAgent/issues

---

**最后更新**: 2026-01-12  
**文档版本**: v2.0.1
