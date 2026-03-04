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

### 📄 Windows 端侧打包 / 离线部署详细指南（推荐工作流）

本部分说明如何在 Windows 上将 Tauri 应用（前端）与 Python FastAPI 后端打包成一个安装包（NSIS `.exe`）。

#### 0. 关键约定（当前仓库默认）

*   **Conda 环境名**：`hk_tauri`
*   **后端打包**：PyInstaller 单文件 `backend.exe`（spec: `backend/build_backend_onefile.spec`）
*   **Tauri sidecar 路径**：`frontend/src-tauri/bin/backend-<target_triple>.exe`
*   **目标 triple（Windows x64 常见）**：`x86_64-pc-windows-msvc`
*   **安装器类型**：NSIS（为避免构建时自动下载 WiX 失败，当前 `tauri.conf.json` 已限定 targets 为 `["nsis"]`）

#### 1. 环境准备 (Windows 开发机)

由于包含 Python 依赖（如 numpy, opencv）和海康 MVS Runtime，建议在 Windows 真机/虚拟机上进行打包。

需要安装/具备：
1.  **Miniconda/Conda**：并已创建 `hk_tauri` 环境（Python 3.10+）。
2.  **Node.js**：建议安装到 `C:\Program Files\nodejs`（本仓库构建时会显式注入 PATH）。
3.  **Rust (stable MSVC)**：用于 Tauri 构建（`cargo-tauri`）。
4.  **海康 MVS**（目标机也需要安装）：
    *   环境变量 `MVCAM_COMMON_RUNENV` 正确（例如 `C:\Program Files (x86)\MVS\Development`）。
    *   DLL 通常位于 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\`。

#### 2. 打包 Python 后端

我们先将 Python 后端打包成 Tauri sidecar（一个 `backend.exe`）。

**步骤**:
1.  安装/同步依赖（确保不会在运行时自动下载依赖）：
    ```powershell
    cd backend
    C:\ProgramData\miniconda3\envs\hk_tauri\python.exe -m pip install -r requirements.txt pyinstaller
    ```
2.  使用 spec 打包（推荐，参数已固化）：
    ```powershell
    C:\ProgramData\miniconda3\envs\hk_tauri\python.exe -m PyInstaller build_backend_onefile.spec --noconfirm
    ```
3.  产物位于：
    *   `backend/dist/backend.exe`

> 说明：后端在 `hik_driver.py` 中已增加 Windows DLL 搜索路径注入（`os.add_dll_directory` + PATH），用于在冻结环境下加载 `MvCameraControl.dll`。

#### 3. 配置 Tauri Sidecar

1.  获取 target triple（只需确认一次）：
    ```powershell
    & "$env:USERPROFILE\.cargo\bin\rustc.exe" -vV | findstr host
    ```
    常见输出：`host: x86_64-pc-windows-msvc`
2.  复制并重命名 sidecar 到 Tauri 目录（注意：当前仓库使用 `src-tauri/bin`）：
    ```powershell
    Copy-Item -Force backend\dist\backend.exe frontend\src-tauri\bin\backend-x86_64-pc-windows-msvc.exe
    ```
3.  核对配置：
    *   `frontend/src-tauri/tauri.conf.json` 中 `bundle.externalBin` 包含 `bin/backend`
    *   `frontend/src-tauri/capabilities/default.json` 已允许 `shell:allow-spawn`（sidecar: backend）
    *   `frontend/src-tauri/src/lib.rs` 会在应用启动时自动拉起后端 sidecar，并在窗口关闭时尝试 kill

#### 4. 处理海康 SDK

海康 SDK 依赖系统级 DLL。
*   **本项目策略**：要求目标机预装 MVS（不把 MVS DLL 打进安装包）。
*   若目标机报错 `MvCameraControl.dll not found`：
    1. 确认安装了 MVS Runtime（且为 64 位运行库）。
    2. 确认 `MVCAM_COMMON_RUNENV` 存在，并重启应用。
    3. 确认 `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\` 下存在 `MvCameraControl.dll`。

#### 5. 构建最终安装包

**一键脚本（推荐）**：
```powershell
cd .
.\build_windows.ps1
```

如需跳过依赖安装（已装过依赖时加速）：
```powershell
.\build_windows.ps1 -SkipBackendDeps -SkipFrontendDeps
```

1.  前端依赖安装与构建（建议使用 `npm ci`）：
    ```powershell
    cd frontend
    $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    & "C:\Program Files\nodejs\npm.cmd" ci
    & "C:\Program Files\nodejs\npm.cmd" run build
    ```
2.  安装 Tauri CLI（首次需要）：
    ```powershell
    & "$env:USERPROFILE\.cargo\bin\cargo.exe" install tauri-cli --locked
    ```
3.  构建安装器：
    ```powershell
    $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    & "$env:USERPROFILE\.cargo\bin\cargo-tauri.exe" build
    ```
4.  安装器输出：
    *   `frontend/src-tauri/target/release/bundle/nsis/*-setup.exe`

> 备注：如果要做 MSI（WiX），需保证构建机可正常下载/安装 WiX Toolset；当前仓库默认走 NSIS 以提升成功率。

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
