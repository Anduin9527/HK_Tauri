# NexusAI 工业视觉缺陷检测平台 (Industrial Vision Defect Detection)

一个基于 Tauri + React + Python (FastAPI/YOLO) 的现代化工业视觉检测应用。

## ✨ 功能特性 (Features)

*   **实时监控**: 集成 Hikvision 工业相机 SDK (MVS) / RTSP  / Webcam，低延迟视频流预览。
*   **AI 缺陷检测**: 内置 YOLOv8 模型，支持实时表面缺陷检测（划痕、异物、缺损等）。
*   **交互式日志**: 实时各类检测事件，支持点击日志查看关联的缺陷图片（包括原图和标注图）。
*   **动态配置**: 支持在线调整模型置信度 (Confidence) 和推理分辨率 (Resolution)，实时生效。
*   **跨平台**: 基于 Tauri 构建，支持 Windows, macOS, Linux。

## 🛠️ 技术栈 (Tech Stack)

*   **Frontend**: React, Vite, TailwindCSS, Lucide Icons, Socket.IO Client
*   **Backend**: Python 3.9+, FastAPI, Uvicorn, OpenCV, Ultralytics YOLO, Socket.IO Server
*   **Core**: Rust (Tauri 2.0)

## 📦 开发指南 (Development)

### 1. 环境准备

确保已安装：
*   [Node.js](https://nodejs.org/) (v16+)
*   [Python](https://www.python.org/) (v3.9+)
*   [Rust](https://www.rust-lang.org/) (用于 Tauri 构建)

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# .\venv\Scripts\activate # Windows

# 安装依赖
pip install -r requirements.txt

# 下载/放入模型文件
# 确保 backend/models/best.onnx 存在
```

### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install
```

### 4. 启动开发环境

**方式 A: 一键启动 (Tauri)**
在 `frontend` 目录下运行：
```bash
npm run tauri dev
```
这将自动编译 Rust 核心，启动前端页面，并尝试连接后端（需确保后端已在 8000 端口运行）。

**注意**: 开发模式下建议先手动启动后端，再启动前端。

**方式 B: 分别启动**

*终端 1 (Backend):*
```bash
cd backend
python main.py
```

*终端 2 (Frontend):*
```bash
cd frontend
npm run tauri dev
```

## 🚀 部署构建 (Deployment)

打包为可执行文件（exe / dmg / appImage）：

```bash
cd frontend
npm run tauri build
```
构建产物将位于 `frontend/src-tauri/target/release/bundle/` 目录下。

## ⚠️ 常见问题

*   **相机无法连接**: 
    *   检查是否已安装 Hikvision MVS SDK Runtime。
    *   macOS 下默认使用 Webcam (0)，如需测试工业相机请在 Windows 环境部署。
*   **日志图片无法加载**:
    *   确保后端 `history/` 目录存在且有写入权限。

## 📂 目录结构

*   `backend/`: Python FastAPI 服务，负责相机控制与 AI 推理。
*   `frontend/`: React UI 界面。
*   `frontend/src-tauri/`: Rust 核心进程配置。
