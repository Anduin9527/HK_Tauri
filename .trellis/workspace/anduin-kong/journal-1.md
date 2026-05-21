# Journal - anduin-kong (Part 1)

> AI development session journal
> Started: 2026-05-18

---



## Session 1: 性能优化：OpenVINO推理、跳帧策略、流循环打包、前端清理

**Date**: 2026-05-21
**Task**: 性能优化：OpenVINO推理、跳帧策略、流循环打包、前端清理
**Branch**: `main`

### Summary

集成OpenVINO推理后端(1.63x加速)，实现推理fire-and-forget跳帧策略，batch流循环resize+draw+encode，前端死代码清理+VideoFeed指数退避重连+依赖瘦身

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `ccc42eb` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

---

## Session 2: 前端界面优化：解耦App.jsx、组件模块化、1080P布局适配、暗黑模式设计

**Date**: 2026-05-21
**Task**: 前端界面优化：解耦App.jsx、组件模块化、1080P布局适配、暗黑模式设计
**Branch**: `main`

### Summary

将 1045 行的巨石组件 App.jsx 解耦重构为模块化架构（3 个自定义 Hook，14 个子组件），优化布局以适配 1080P 屏幕的 80% 尺寸（1536x864），完全去除日间模式（统一极客暗黑主题），增加微交互和动效，保持与原有 Python 后端 API 及 Tauri 指令的无缝对接。

### Main Changes

1. **自定义 Hook 提取**：
   - `useBackendConnection.js`：提取 Socket.IO 消息接收、帧率、CPU负载及手动/自动模式控制逻辑。
   - `useCameraManager.js`：提取海康相机发现、绑定槽位切换、推流连接/断开控制逻辑。
   - `useSettings.js`：提取模型切换、后端推理引擎选择、参数保存及本地数据文件夹打开指令。

2. **视图组件模块化**：
   - `components/layout/`：创建 `Sidebar.jsx` (左侧状态/导航栏) 和 `Header.jsx` (顶部标题与就绪状态)。
   - `components/dashboard/`：提取 `VideoGrid.jsx` (2×2多路画面及单路最大化)、`ControlBar.jsx` (主操作控制台及调试文件上传)、`StatsPanel.jsx` (状态概览卡片组) 和 `AlertFeed.jsx` (实时告警滚动面板)。
   - `components/logs/`：创建 `LogsView.jsx` (日志历史、全文模糊搜索、高/中/低级别过滤、缺陷图片查看)。
   - `components/settings/`：创建 `SettingsView.jsx` (参数容器及动作按钮)、`ModelSelector.jsx` (模型及后端系列)、`CameraParamsCard.jsx` (通道独立曝光/增益手风琴卡片) 和 `DetectionConfig.jsx` (置信度/冷却时间滑块及输入分辨率切换)。
   - `components/shared/`：创建 `ImagePreviewModal.jsx` (全屏大图预览及遮罩点击关闭)。

3. **视觉设计与交互**：
   - 重构 `App.css`：去掉白天/黑夜模式，统一为高保真暗黑毛玻璃风格；引入过渡动画 (`fadeSlideIn`)、滑块微发光动效、无摄像头信号时的扫描线动效 (`.scan-line`)，以及卡片悬浮动效 (`.hover-lift`)。
   - 修改 `tauri.conf.json`：设置默认启动窗口为 `1536 × 864` 并默认居中，确保在 1080p 屏幕下优雅占满约 80% 的比例。

### Testing

- 代码在 React 19、Vite 7 下通过语法检查与组件树构建。
- 与本地/远程后端接口数据格式和事件触发的映射关系完全对齐。

### Status

[OK] **Completed**

### Next Steps

- 推送更改，在远程 Windows 电脑上运行以验证海康 SDK 实际连接与视频流渲染。

