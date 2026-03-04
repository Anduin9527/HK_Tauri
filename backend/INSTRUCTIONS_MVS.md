# 海康机器人工业相机 (MVS SDK) 配置指南 / MVS SDK Setup Guide

为了连接海康工业相机 (HikRobot Industrial Camera)，我们需要使用官方的 Python SDK。
To connect to the HikRobot Industrial Camera, we need the official Python SDK.

## 1. 下载与安装 / Download & Install

### Windows (部署环境 / Deployment)
1.  访问海康机器人官网下载 **MVS (Machine Vision Studio)** 客户端。
    *   下载地址通常在：服务支持 -> 下载中心 -> 客户端软件 -> MVS。
2.  安装时选择 "Full Installation" 以确保包含驱动和开发包。

### MacOS (开发环境 / Development)
1.  同样在官网下载 **MVS for MacOS** (如果有提供) 或者使用 Windows 虚拟机/远程桌面进行调试。
    *   *注：MacOS 版本的 MVS 可能功能有限，主要是查看相机是否在线。*

## 2. 提取 Python SDK 文件 / Extract Python SDK

安装完成后，请在安装目录中寻找 Python 示例代码文件夹：
*   **Windows**: `C:\Program Files (x86)\MVS\Development\Samples\Python\BasicDemo` (类似路径)
*   或者在安装包解压后的目录中寻找。

你需要复制 **`MvImport`** 文件夹，并将其粘贴到本项目的 `backend` 目录下。

### 目录结构应如下 / Expected Structure:
```text
backend/
  ├── main.py
  ├── camera.py
  ├── detector.py
  ├── models/
  └── MvImport/           <--- 必须包含这个文件夹 / Must include this folder
      ├── __init__.py
      ├── CameraParams_const.py
      ├── CameraParams_header.py
      ├── MvCameraControl_class.py
      ├── MvErrorDefine_const.py
      └── PixelType_header.py
```

## 3. 代码适配 / Code Adaptation

我将更新 `camera.py`，使其能够：
1.  自动检测是否存在 `MvImport` 库。
2.  如果存在且有相机连接，优先使用海康相机。
3.  如果不存在 (比如在 MacOS 上没有拷入库时)，自动回退到普通 Webcam/RTSP 模式方便调试。
