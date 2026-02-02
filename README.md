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

### 📄 Windows 离线部署详细指南

本部分详细说明如何在 Windows 环境下将 Tauri 应用与 Python 后端打包为独立的 `.exe` 安装包，适用于无网络工厂环境部署。

#### 1. 环境准备 (Windows 开发机)

由于包含 Python 依赖（如 numpy, opencv）和海康威视 DLL，**强烈建议在 Windows 虚拟机或真机上进行打包操作**。

需要安装：
1.  **Python 3.10+**: 确保加入 PATH。
2.  **Node.js & Rust**: Tauri 的标准开发环境。
3.  **海康威视 MVS SDK**: 安装客户端以获取必要的 DLL 和驱动。
4.  **PyInstaller**: `pip install pyinstaller`

#### 2. 打包 Python 后端

我们需先将 Python 后端打包成独立的 sidecar。

**步骤**:
1.  进入 `backend` 目录。
2.  确保 `MvImport` 文件夹存在。
3.  执行 PyInstaller 命令（包含所有依赖）：
    ```powershell
    pyinstaller --noconfirm --onefile --windowed --name backend ^
        --add-data "models;models" ^
        --add-data "history;history" ^
        --add-data "MvImport;MvImport" ^
        --hidden-import socketio ^
        --hidden-import uvicorn ^
        --hidden-import engineio.async_drivers.asgi ^
        main.py
    ```
4.  在 `dist/` 目录找到 `backend.exe`。

#### 3. 配置 Tauri Sidecar

1.  **获取 Target Triple**: 运行 `rustc -vV | findstr host` (例如 `x86_64-pc-windows-msvc`)。
2.  **复制二进制文件**: 将 `backend.exe` 复制到 `frontend/src-tauri/binaries/` 并重命名为 `backend-x86_64-pc-windows-msvc.exe`。
3.  **主要配置**: 确保 `tauri.conf.json` 中 `bundle.externalBin` 包含 `["binaries/backend"]`。

#### 4. 处理海康 SDK

海康 SDK 依赖系统级 DLL。
*   **开发打包时**: 无需特殊操作，只要运行环境有驱动。
*   **部署时**: 推荐在目标机器安装 MVS 客户端。如果在完全纯净环境运行绿色版，需手动将海康 `Runtime` 目录下的 DLL 复制到程序运行目录。

#### 5. 构建最终安装包

```powershell
cd frontend
npm run tauri build
```
生成的 `.exe` 安装包即可分发到无网工厂电脑。

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
