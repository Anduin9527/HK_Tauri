import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import './App.css';
import { Play, Square, Settings, Luggage, AlertTriangle, Cpu, Minimize2, Image as ImageIcon, RefreshCw, Link, Link2Off, Camera, Zap, Sun, Moon, Activity, FolderOpen } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import VideoFeed from './components/VideoFeed';
import clsx from 'clsx';

// Constants
const BACKEND_URL = "http://localhost:8000";
const VIDEO_STREAM_URL = `${BACKEND_URL}/video_feed`;

function App() {
  const [streaming, setStreaming] = useState(false);
  const [stats, setStats] = useState({ cpu: 0 });
  const [cameraFps, setCameraFps] = useState({});
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [debugImage, setDebugImage] = useState(null);
  const [sceneMode, setSceneMode] = useState('day');
  const [slotBusy, setSlotBusy] = useState({0: false, 1: false, 2: false, 3: false});
  const [globalBusy, setGlobalBusy] = useState(false);

  // Camera Management State
  const [availableCameras, setAvailableCameras] = useState([]);
  const [slotMapping, setSlotMapping] = useState({0: null, 1: null, 2: null, 3: null});
  const [loadingCameras, setLoadingCameras] = useState(false);
  const [autoInference, setAutoInference] = useState(false);
  
  // Fullscreen State for a specific slot
  const [maximizedSlot, setMaximizedSlot] = useState(null); // null or slotId (0-3)

  // Simulate stats update
  useEffect(() => {
    if (!streaming) return;
    const interval = setInterval(() => {
      // Only update simulated stats if no real data (fallback)
      // In real scenario, `fetchStats` updates `stats`
      // We keep this just for visual liveness if backend is dumb
    }, 1000);
    return () => clearInterval(interval);
  }, [streaming]);

  const addLog = (title, message, severity, attachment = null, time = null) => {
    setLogs(prev => [{ id: Date.now(), title, message, severity, attachment, time: time || new Date().toLocaleTimeString() }, ...prev].slice(0, 50));
  };

  // Socket.IO Connection
  useEffect(() => {
    const socket = io(BACKEND_URL);

    socket.on('log_message', (data) => {
      addLog(data.title, data.message, data.severity, data.attachment, data.time);
    });

    socket.on('camera_fps', (data) => {
      if (data && data.cameras) setCameraFps(data.cameras);
    });

    return () => socket.disconnect();
  }, []);

  // Fetch Available Cameras
  const refreshCameras = async () => {
    setLoadingCameras(true);
    try {
      const res = await fetch(`${BACKEND_URL}/cameras/discover`);
      const data = await res.json();
      if (data?.sdk_required && data?.sdk_available === false) {
        addLog("错误", data.sdk_hint || "未检测到海康 SDK，请先安装后重启。", "high");
      }
      setAvailableCameras(data.cameras || []);
      if (data.cameras?.length > 0) {
        addLog("系统", `发现 ${data.cameras.length} 个可用设备`, "info");
      } else {
        addLog("系统", "未发现可用设备", "medium");
      }
    } catch (e) {
      addLog("错误", "无法获取设备列表: " + e.message, "high");
    } finally {
      setLoadingCameras(false);
    }
  };

  // Initial load
  useEffect(() => {
    refreshCameras();
  }, []);

  useEffect(() => {
    fetch(`${BACKEND_URL}/config/mode`)
      .then(res => res.json())
      .then(data => {
        if (typeof data.manual_mode === 'boolean') {
          setAutoInference(!data.manual_mode);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch(`${BACKEND_URL}/config/scene`)
      .then(res => res.json())
      .then(data => {
        if (data.scene_mode === 'day' || data.scene_mode === 'night') {
          setSceneMode(data.scene_mode);
        }
      })
      .catch(() => {});
  }, []);

  const toggleScene = async () => {
    const newMode = sceneMode === 'day' ? 'night' : 'day';
    try {
      setSceneMode(newMode);
      const res = await fetch(`${BACKEND_URL}/config/scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_mode: newMode })
      });
      if (!res.ok) throw new Error("Failed to save scene");
      addLog("系统", `切换至${newMode === 'day' ? '日间' : '夜间'}模式`, "info");
    } catch (err) {
      addLog("错误", "场景切换失败", "high");
    }
  };

  const connectCamera = async (slotId, cameraIndex) => {
    if (globalBusy || slotBusy?.[slotId]) return;
    setSlotBusy(prev => ({ ...prev, [slotId]: true }));
    try {
      const res = await fetch(`${BACKEND_URL}/cameras/${slotId}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_index: parseInt(cameraIndex) })
      });
      
      if (res.ok) {
        const data = await res.json();
        const cam = availableCameras.find(c => c.index === parseInt(cameraIndex));
        
        setSlotMapping(prev => ({
          ...prev, 
          [slotId]: cam || { index: cameraIndex, name: `Camera ${cameraIndex}` }
        }));
        
        addLog("系统", `Slot ${slotId} 已绑定设备: ${cam?.name || cameraIndex}`, "info");
        
        // Auto start streaming if at least one cam is connected
        if (!streaming) setStreaming(true);
      } else {
        const msg = res.status === 409 ? "设备被占用，请稍后重试" : "连接失败";
        addLog("错误", `Slot ${slotId} ${msg}`, "high");
      }
    } catch (e) {
      addLog("错误", "连接请求异常: " + e.message, "high");
    } finally {
      setSlotBusy(prev => ({ ...prev, [slotId]: false }));
    }
  };

  const disconnectCamera = async (slotId) => {
    if (globalBusy || slotBusy?.[slotId]) return;
    setSlotBusy(prev => ({ ...prev, [slotId]: true }));
    try {
      await fetch(`${BACKEND_URL}/cameras/${slotId}/disconnect`, { method: 'POST' });
      setSlotMapping(prev => {
        const next = { ...prev, [slotId]: null };
        const anyConnected = Object.values(next).some(Boolean);
        if (!anyConnected) setStreaming(false);
        return next;
      });
      addLog("系统", `Slot ${slotId} 已断开连接`, "info");
    } catch (e) {
       console.error(e);
    } finally {
      setSlotBusy(prev => ({ ...prev, [slotId]: false }));
    }
  };

  const disconnectAllCameras = async () => {
    if (globalBusy) return;
    setGlobalBusy(true);
    try {
      const res = await fetch(`${BACKEND_URL}/status`);
      const data = await res.json();
      const active = (data.cameras || []).filter(c => c.connected);
      if (active.length === 0) return;

      for (const c of active) {
        await fetch(`${BACKEND_URL}/cameras/${c.id}/disconnect`, { method: 'POST' });
      }
      setSlotMapping({0: null, 1: null, 2: null, 3: null});
      setMaximizedSlot(null);
      setStreaming(false);
      addLog("系统", "已断开所有摄像头连接", "info");
    } catch (e) {
      addLog("错误", "断开所有摄像头失败: " + e.message, "high");
    } finally {
      setGlobalBusy(false);
    }
  };

  const toggleStream = async () => {
    try {
      if (globalBusy) return;
      if (streaming) {
        setStreaming(false);
        await disconnectAllCameras();
      } else {
        const anyConnected = Object.values(slotMapping).some(Boolean);
        if (!anyConnected) {
          addLog("系统", "请先绑定至少一路摄像头", "medium");
          return;
        }
        setStreaming(true);
      }
    } catch (e) {
      console.error("Error toggling stream:", e);
    }
  };

  const toggleSceneMode = async () => {
    const nextMode = sceneMode === 'day' ? 'night' : 'day';
    try {
      const res = await fetch(`${BACKEND_URL}/config/scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_mode: nextMode })
      });
      const data = await res.json();
      if (data.status === 'updated') {
        setSceneMode(nextMode);
        addLog("配置", `场景模式切换为: ${nextMode === 'day' ? '日间' : '夜间'}`, "info");
      } else {
        addLog("错误", `场景模式切换失败: ${data.error || 'Unknown'}`, "high");
      }
    } catch (e) {
      addLog("错误", "场景模式切换异常: " + e.message, "high");
    }
  };

  const toggleAutoInference = async () => {
    try {
      // Logic Explanation:
      // If current is AUTO (autoInference=true), user wants MANUAL (manual_mode=true).
      // If current is MANUAL (autoInference=false), user wants AUTO (manual_mode=false).
      
      const nextIsManual = autoInference; // If auto is true, next manual is true.
      
      await fetch(`${BACKEND_URL}/config/mode`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manual_mode: nextIsManual })
      });
      
      setAutoInference(!nextIsManual); // Update local state: if next is manual, auto is false
    } catch (e) {
      addLog("错误", "切换模式失败: " + e.message, "high");
    }
  };

  const triggerDetection = async () => {
    try {
      // Changed endpoint from /control/trigger to /trigger/detect to match backend
      const res = await fetch(`${BACKEND_URL}/trigger/detect`, { method: 'POST' });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      // addLog("操作", "已发送触发指令", "info");
    } catch (e) {
      addLog("错误", "触发失败: " + e.message, "high");
    }
  };

  // Poll for backend status/stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/status`);
        const data = await res.json();

        // Sync connection status from backend if needed (optional, for consistency)
        // data.cameras array contains {id, connected, index}
        if (data.cameras) {
             // We could sync slotMapping here if we wanted bidirectional sync
        }

        if (data.model_loaded) { 
          setStats(prev => ({
            cpu: Math.round(15 + Math.random() * 10),
          }));
        }
      } catch (e) {
        // console.log("Backend offline");
      }
    };

    const interval = setInterval(fetchStats, 2000);
    return () => {
      clearInterval(interval);
    };
  }, [streaming]);

  return (
    <div data-scene={sceneMode} className="app-root h-screen w-screen flex bg-[var(--bg-dark)] text-[var(--text-main)] overflow-hidden relative transition-colors duration-500">

      {/* Debug Image Modal */}
      {debugImage && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 md:p-8"
          onClick={() => setDebugImage(null)}
        >
          <div
            className="relative bg-[var(--bg-card)] border border-[var(--border)] rounded-xl shadow-2xl max-w-[95vw] max-h-[95vh] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => setDebugImage(null)}
              className="absolute top-4 right-4 z-20 p-2 rounded-full bg-black/60 text-white hover:bg-red-500/80 transition-colors backdrop-blur-md"
            >
              <Minimize2 size={20} />
            </button>

            {/* Image Container */}
            <div className="flex-1 overflow-auto flex items-center justify-center min-w-[320px] min-h-[240px] p-1 bg-black/20 rounded-t-xl">
              <img
                src={debugImage}
                alt="Detection Result"
                className="max-w-full max-h-[85vh] object-contain rounded-lg"
              />
            </div>

            {/* Footer */}
            <div className="p-3 bg-white/5 border-t border-white/5 text-center shrink-0">
              <p className="text-xs font-mono text-gray-400">点击背景关闭 • 检测结果预览</p>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar navigation */}
      <aside className="w-20 lg:w-64 border-r border-[var(--border)] flex flex-col glass z-20 transition-colors duration-500">
        <div className="p-6 flex items-center justify-between border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-[0_0_15px_rgba(79,70,229,0.5)]">
              <Luggage size={18} className="text-white" />
            </div>
            <span className="font-bold tracking-wide hidden lg:block">旅行箱<span className="text-indigo-400">缺陷检测</span></span>
          </div>
          <button 
            onClick={toggleScene}
            className="hidden lg:flex p-2 rounded-lg hover:bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
            title={sceneMode === 'day' ? "切换夜间模式" : "切换日间模式"}
          >
            {sceneMode === 'day' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {[
            { id: 'dashboard', icon: Activity, label: '实时监控' },
            { id: 'logs', icon: AlertTriangle, label: '缺陷日志' },
            { id: 'settings', icon: Settings, label: '系统设置' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={clsx(
                "w-full flex items-center gap-3 p-3 rounded-xl transition-all duration-300 group",
                activeTab === item.id
                  ? "bg-indigo-600/10 text-indigo-400 border border-indigo-600/20"
                  : "text-[var(--text-muted)] hover:bg-[var(--bg-card)] hover:text-[var(--text-main)]"
              )}
            >
              <item.icon size={20} className={clsx("transition-transform group-hover:scale-110", activeTab === item.id && "text-indigo-400")} />
              <span className="hidden lg:block font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-[var(--border)]">
          <div className="p-3 bg-[var(--bg-card)] rounded-xl border border-[var(--border)]">
            <div className="flex items-center gap-3 mb-2">
              <Cpu size={16} className="text-emerald-400" />
              <span className="text-xs font-mono text-[var(--text-muted)]">INTEL 系统状态</span>
            </div>
            <div className="h-1 w-full bg-[var(--bg-dark)] rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 w-[35%]" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-hidden">

        {/* Top Bar for Status */}
        <header className="h-16 border-b border-[var(--border)] flex items-center justify-between px-8 glass z-10">
          <h1 className="text-lg font-semibold text-[var(--text-main)]">
            旅行箱表面缺陷检测系统 · {activeTab === 'dashboard' ? '实时推理监控' : activeTab === 'logs' ? '缺陷日志历史' : '系统设置'}
          </h1>
          <div className="flex items-center gap-4">
            <div className="px-3 py-1 bg-[var(--bg-card)] rounded-full border border-[var(--border)] flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-mono text-green-400">系统就绪</span>
            </div>
          </div>
        </header>

        <div className="flex-1 p-6 overflow-y-auto">

          {/* Dashboard View */}
          {activeTab === 'dashboard' && (
            <div className="flex flex-col xl:flex-row gap-6 h-full">

              {/* Video Feed Area (2x2 Grid) */}
              <div className="flex-1 flex flex-col gap-6 min-h-0 relative">
                <div className={clsx(
                  "grid gap-4 h-full min-h-[500px] transition-all duration-300",
                  maximizedSlot !== null ? "grid-cols-1 grid-rows-1" : "grid-cols-2 grid-rows-2"
                )}>
                  {[0, 1, 2, 3].map(slotId => {
                    // If a slot is maximized, hide others
                    if (maximizedSlot !== null && maximizedSlot !== slotId) return null;
                    
                    return (
                    <div key={slotId} className="relative w-full h-full min-h-0 group/slot transition-all duration-500">
                      
                      {/* Slot Header Controls */}
                      <div className="absolute top-2 left-2 z-20 flex items-center gap-2">
                        <div className="px-2 py-1 bg-black/60 rounded text-xs font-mono text-white/70 backdrop-blur-md">
                          CAM {slotId + 1}
                        </div>
                        
                        {/* Camera Selector */}
                        <div className="relative">
                           {!slotMapping[slotId] ? (
                              <select 
                                className="h-6 pl-2 pr-6 bg-indigo-500/20 border border-indigo-500/30 text-xs text-white rounded cursor-pointer hover:bg-indigo-500/30 transition-colors appearance-none outline-none"
                                onChange={(e) => {
                                  if (e.target.value !== "") connectCamera(slotId, e.target.value);
                                }}
                                value=""
                                disabled={loadingCameras || globalBusy || slotBusy?.[slotId]}
                              >
                                <option value="" disabled>选择设备...</option>
                                {availableCameras.map(cam => (
                                  <option key={cam.index} value={cam.index}>
                                    {cam.name} ({cam.type})
                                  </option>
                                ))}
                              </select>
                           ) : (
                              <div className="flex items-center gap-1">
                                <span className="h-6 px-2 flex items-center bg-green-500/20 border border-green-500/30 text-xs text-green-300 rounded">
                                  {slotMapping[slotId].name}
                                </span>
                                <button 
                                  onClick={() => disconnectCamera(slotId)}
                                  className="h-6 w-6 flex items-center justify-center bg-black/60 hover:bg-red-500/80 rounded text-white transition-colors"
                                  title="断开连接"
                                  disabled={globalBusy || slotBusy?.[slotId]}
                                >
                                  <Link2Off size={12} />
                                </button>
                              </div>
                           )}
                           
                           {/* Arrow icon for select (hack since appearance-none) */}
                           {!slotMapping[slotId] && (
                             <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-white/50">
                               <Link size={10} />
                             </div>
                           )}
                        </div>
                      </div>

                      <VideoFeed
                        streamUrl={streaming && slotMapping[slotId] ? `${BACKEND_URL}/video_feed/${slotId}` : ""}
                        isConnected={streaming && !!slotMapping[slotId]}
                        onMaximize={() => setMaximizedSlot(maximizedSlot === slotId ? null : slotId)}
                        isMaximized={maximizedSlot === slotId}
                        fps={cameraFps?.[slotId]}
                        autoInference={autoInference}
                      />
                    </div>
                  )})}
                </div>

                {/* Control Bar */}
                <div className="p-4 glass-card rounded-xl flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-300">多路摄像头控制</h3>
                      <p className="text-xs text-gray-500">Hikvision Matrix System (4CH)</p>
                    </div>
                    <button 
                      onClick={refreshCameras}
                      disabled={loadingCameras || globalBusy || Object.values(slotBusy).some(Boolean)}
                      className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
                      title="刷新设备列表"
                    >
                      <RefreshCw size={16} className={clsx(loadingCameras && "animate-spin")} />
                    </button>
                  </div>
                  
                  <div className="flex gap-4">
                    {/* Mode Toggle */}
                    <button
                      onClick={toggleAutoInference}
                      className={clsx(
                        "px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 border",
                        autoInference
                          ? "bg-indigo-600/20 text-indigo-400 border-indigo-500/50"
                          : "bg-white/5 text-gray-400 border-white/10 hover:bg-white/10"
                      )}
                      title={autoInference ? "当前: 自动连续检测" : "当前: 手动触发模式"}
                    >
                      <Zap size={16} className={clsx(autoInference && "fill-current")} />
                      <span className="hidden md:inline">{autoInference ? "自动模式" : "手动模式"}</span>
                    </button>

                    {/* Manual Trigger Button (Only in Manual Mode) */}
                    {!autoInference && (
                      <button
                        onClick={triggerDetection}
                        disabled={!streaming || globalBusy}
                        className="px-6 py-2 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.4)] disabled:opacity-50 disabled:shadow-none"
                      >
                        <Camera size={16} />
                        <span>单次检测</span>
                      </button>
                    )}

                    <div className="w-px bg-white/10 mx-2" />

                    <button
                      onClick={toggleStream}
                      disabled={globalBusy}
                      className={clsx(
                        "px-6 py-2 rounded-lg font-medium transition-all shadow-[0_4px_14px_0_rgba(0,0,0,0.39)] hover:shadow-none hover:translate-y-[1px] flex items-center gap-2",
                        streaming
                          ? "bg-red-500/10 text-red-400 border border-red-500/50 hover:bg-red-500/20"
                          : "bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
                      )}
                    >
                      {streaming ? <Square size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
                      {streaming ? "停止所有推流" : "启动全网监控"}
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Panel: Stats & Logs */}
              <div className="w-full xl:w-96 flex flex-col gap-6 h-full shrink-0">
                {/* Stats Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="glass-card p-4 rounded-xl flex flex-col gap-1">
                    <span className="text-xs text-gray-400 uppercase tracking-wider">场景模式</span>
                    <button
                      onClick={toggleSceneMode}
                      className={clsx(
                        "mt-2 px-3 py-2 rounded-lg border text-sm font-medium transition-all flex items-center justify-center gap-2",
                        sceneMode === 'day'
                          ? "bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/15"
                          : "bg-indigo-500/10 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/15"
                      )}
                      title={sceneMode === 'day' ? "当前: 日间模式" : "当前: 夜间模式"}
                    >
                      {sceneMode === 'day' ? <Sun size={16} /> : <Moon size={16} />}
                      {sceneMode === 'day' ? "日间" : "夜间"}
                    </button>
                  </div>
                  <div className="glass-card p-4 rounded-xl flex flex-col gap-1">
                    <span className="text-xs text-gray-400 uppercase tracking-wider">CPU (估算)</span>
                    <span className="text-2xl font-bold font-mono text-indigo-400">{stats.cpu}%</span>
                  </div>
                </div>

                {/* Image Upload Debug */}
                <div className="glass-card p-4 rounded-xl flex flex-col gap-3">
                  <h3 className="text-sm font-medium text-gray-300 border-b border-white/5 pb-2">图片检测调试</h3>
                  <div className="flex gap-2">
                    <label className="flex-1 cursor-pointer bg-white/5 hover:bg-white/10 border border-dashed border-white/20 rounded-lg p-3 flex flex-col items-center justify-center transition-colors">
                      <span className="text-xs text-gray-400">点击上传图片</span>
                      <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={async (e) => {
                          const file = e.target.files[0];
                          if (!file) return;

                          const formData = new FormData();
                          formData.append('file', file);

                          try {
                            addLog("调试", "正在上传图片...", "medium");
                            const res = await fetch(`${BACKEND_URL}/predict/image`, {
                              method: 'POST',
                              body: formData
                            });

                            if (res.status === 400) {
                              const data = await res.json();
                              addLog("操作失败", data.error, "high");
                              alert(data.error);
                              return;
                            }

                            if (res.ok) {
                              const data = await res.json();
                              // Backend returns { image_url: "..." }
                              if (data.image_url) {
                                setDebugImage(data.image_url);
                                addLog("调试", "图片检测完成", "medium", data.image_url);
                              } else {
                                addLog("错误", "未返回图片地址", "high");
                              }
                            } else {
                              addLog("错误", "上传失败: " + res.statusText, "high");
                            }
                          } catch (err) {
                            console.error(err);
                            addLog("错误", "连接失败: " + err.message, "high");
                          }
                        }}
                      />
                    </label>
                  </div>
                </div>

                {/* Recent Alerts */}
                <div className="glass-card flex-1 rounded-xl p-0 overflow-hidden flex flex-col">
                  <div className="p-4 border-b border-[var(--border)] bg-[var(--bg-card)]">
                    <h3 className="text-sm font-medium">最近告警</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {logs.length === 0 ? (
                      <div className="text-center text-[var(--text-muted)] text-sm py-10">暂无检测记录</div>
                    ) : (
                      logs.map(log => (
                        <div key={log.id} className="flex gap-3 items-start p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] hover:border-indigo-500/30 transition-colors">
                          <div className="mt-1">
                            <AlertTriangle size={16} className={log.severity === 'high' ? 'text-red-400' : 'text-yellow-400'} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-baseline mb-1">
                              <h4 className="text-sm font-medium text-[var(--text-main)] truncate">{log.title}</h4>
                              <span className="text-[10px] text-[var(--text-muted)] font-mono">{log.time}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <p className="text-xs text-[var(--text-muted)] line-clamp-2">{log.message}</p>
                              {log.attachment && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setDebugImage(log.attachment); }}
                                  className="p-1 hover:bg-[var(--bg-glass)] rounded text-indigo-400"
                                  title="查看图片"
                                >
                                  <ImageIcon size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Logs View */}
          {activeTab === 'logs' && (
            <div className="flex flex-col h-full gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium text-[var(--text-main)]">系统运行日志</h2>
                <button
                  onClick={() => {
                    // Refresh logs
                    fetch(`${BACKEND_URL}/logs?lines=100`)
                      .then(res => res.json())
                      .then(data => setLogs(data.logs.map((l, i) => ({ ...l, id: i })) || []));
                  }}
                  className="px-4 py-2 bg-[var(--bg-card)] hover:bg-[var(--bg-glass)] rounded-lg text-sm text-[var(--text-main)] transition-colors"
                >
                  刷新日志
                </button>
              </div>
              <div className="flex-1 overflow-auto rounded-xl border border-[var(--border)] bg-[var(--bg-dark)]">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[var(--bg-card)] text-[var(--text-muted)] sticky top-0 backdrop-blur-md">
                    <tr>
                      <th className="p-4 font-medium">时间</th>
                      <th className="p-4 font-medium">级别</th>
                      <th className="p-4 font-medium">模块</th>
                      <th className="p-4 font-medium w-full">详情</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {logs.map((log, i) => (
                      <tr key={i} className="hover:bg-[var(--bg-card)] transition-colors">
                        <td className="p-4 font-mono text-[var(--text-muted)] whitespace-nowrap">{log.time}</td>
                        <td className="p-4">
                          <span className={clsx(
                            "px-2 py-1 rounded text-xs font-medium uppercase",
                            log.severity === 'high' ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                              log.severity === 'medium' ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" :
                                "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          )}>
                            {log.severity || 'INFO'}
                          </span>
                        </td>
                        <td className="p-4 text-[var(--text-main)] whitespace-nowrap">{log.title}</td>
                        <td className="p-4 text-gray-400">
                          <div className="flex items-center gap-2">
                            <span>{log.message}</span>
                            {log.attachment && (
                              <button
                                onClick={() => setDebugImage(log.attachment)}
                                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20"
                              >
                                <ImageIcon size={12} />
                                查看图片
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Settings View */}
          {activeTab === 'settings' && (
            <SettingsPanel addLog={addLog} />
          )}

          {/* Placeholder for other tabs */}
          {activeTab !== 'dashboard' && activeTab !== 'logs' && activeTab !== 'settings' && (
            <div className="flex items-center justify-center h-full text-gray-500">
              功能开发中...
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function SettingsPanel({ addLog }) {
  const [conf, setConf] = useState(0.25);
  const [imgsz, setImgsz] = useState(640);
  const [logInterval, setLogInterval] = useState(10);
  const [modelType, setModelType] = useState('auto');
  const [modelName, setModelName] = useState('yolo26s');
  const [availableModels, setAvailableModels] = useState([]);
  const [cameraParams, setCameraParams] = useState({
    "0": { exposure_time_us: 50000, gain_db: 0 },
    "1": { exposure_time_us: 50000, gain_db: 0 },
    "2": { exposure_time_us: 50000, gain_db: 0 },
    "3": { exposure_time_us: 50000, gain_db: 0 },
  });
  const [loading, setLoading] = useState(false);

  const openDataFolder = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/paths`);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`路径接口异常: ${res.status} ${text || res.statusText}`);
      }
      const data = await res.json();
      const target = data?.history_dir || data?.data_dir;
      if (!target) {
        throw new Error("未返回有效路径");
      }
      await invoke('open_path', { path: target });
      addLog("系统", "已打开数据文件夹", "info");
    } catch (e) {
      addLog("错误", "无法打开文件夹: " + (e?.message || String(e)), "high");
    }
  };

  useEffect(() => {
    fetch(`${BACKEND_URL}/models`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data.models)) setAvailableModels(data.models);
        if (data.active_model_name) setModelName(data.active_model_name);
      })
      .catch(() => {});

    fetch(`${BACKEND_URL}/config/settings`)
      .then(res => res.json())
      .then(data => {
        if (data.conf) setConf(data.conf);
        if (data.imgsz) setImgsz(data.imgsz);
        if (data.log_interval) setLogInterval(data.log_interval);
        if (data.model_type) setModelType(data.model_type);
        if (data.model_name) setModelName(data.model_name);
        if (!data.model_type && data.active_model_type) setModelType(data.active_model_type);
        if (data.camera_params) setCameraParams(data.camera_params);
      })
      .catch(e => console.error(e));
  }, []);

  const applyModelSelection = async (nextName, nextType) => {
    setLoading(true);
    setModelName(nextName);
    setModelType(nextType);
    try {
      const res = await fetch(`${BACKEND_URL}/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conf, imgsz, log_interval: logInterval, model_type: nextType, model_name: nextName, camera_params: cameraParams })
      });
      const data = await res.json();
      if (data.status === 'updated') {
        addLog("配置", `模型切换为: ${nextName} / ${nextType}`, "info");
      } else {
        addLog("错误", `模型切换失败: ${data.error || 'Unknown'}`, "high");
      }
    } catch (e) {
      addLog("错误", "模型切换异常: " + e.message, "high");
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conf, imgsz, log_interval: logInterval, model_type: modelType, model_name: modelName, camera_params: cameraParams })
      });
      const data = await res.json();
      if (data.status === 'updated') {
        addLog("配置", "系统参数已保存", "info");
      } else {
        addLog("错误", "保存失败", "high");
      }
    } catch (e) {
      addLog("错误", "保存异常: " + e.message, "high");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-[var(--text-main)]">系统参数配置</h2>
        <p className="text-[var(--text-muted)]">调整检测模型的灵敏度、即时处理参数及告警频率。</p>
      </div>

      <div className="p-6 glass-card rounded-xl space-y-8">
        
        {/* Data Folder Access */}
        <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-between">
            <div>
                <h3 className="text-sm font-medium text-indigo-300">数据与日志</h3>
                <p className="text-xs text-indigo-200/60">查看后端运行日志 (backend.log) 和历史检测图片</p>
            </div>
            <button
                onClick={openDataFolder}
                className="px-4 py-2 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
                <FolderOpen size={16} />
                打开文件夹
            </button>
        </div>

        {/* Model Selection */}
        <div className="space-y-4">
          <label className="text-sm font-medium text-[var(--text-main)]">推理模型 (Model)</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <div className="text-xs text-[var(--text-muted)]">模型系列</div>
              <select
                value={modelName}
                onChange={(e) => applyModelSelection(e.target.value, modelType)}
                disabled={loading}
                className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded px-3 py-2 text-sm text-[var(--text-main)]"
              >
                {(availableModels.length ? availableModels.map(m => m.name) : ['yolo26s']).map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <div className="text-xs text-[var(--text-muted)]">推理后端</div>
              <select
                value={modelType}
                onChange={(e) => applyModelSelection(modelName, e.target.value)}
                disabled={loading}
                className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded px-3 py-2 text-sm text-[var(--text-main)]"
              >
                <option value="auto">auto (优先 ONNX)</option>
                <option value="onnx">onnx</option>
                <option value="pt">pt</option>
              </select>
            </div>
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            best.* 会被视为 yolo26s 的兼容别名；支持同系列多版本文件名。
          </p>
        </div>

        {/* Camera Parameters */}
        <div className="space-y-4">
          <label className="text-sm font-medium text-[var(--text-main)]">相机参数 (每路)</label>
          <div className="space-y-3">
            {["0", "1", "2", "3"].map((slotKey) => (
              <div key={slotKey} className="grid grid-cols-3 gap-3 items-center bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-3">
                <div className="text-sm text-[var(--text-main)]">Slot {slotKey}</div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--text-muted)] whitespace-nowrap">曝光(µs)</span>
                  <input
                    type="number"
                    min="1"
                    step="100"
                    value={cameraParams?.[slotKey]?.exposure_time_us ?? 50000}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      setCameraParams(prev => ({
                        ...prev,
                        [slotKey]: { ...(prev?.[slotKey] || {}), exposure_time_us: Number.isFinite(v) ? v : 50000 }
                      }));
                    }}
                    className="w-full bg-[var(--bg-dark)] border border-[var(--border)] rounded px-2 py-1 text-sm text-[var(--text-main)]"
                    disabled={loading}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--text-muted)] whitespace-nowrap">增益(dB)</span>
                  <input
                    type="number"
                    step="0.1"
                    value={cameraParams?.[slotKey]?.gain_db ?? 0}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      setCameraParams(prev => ({
                        ...prev,
                        [slotKey]: { ...(prev?.[slotKey] || {}), gain_db: Number.isFinite(v) ? v : 0 }
                      }));
                    }}
                    className="w-full bg-[var(--bg-dark)] border border-[var(--border)] rounded px-2 py-1 text-sm text-[var(--text-main)]"
                    disabled={loading}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            保存后会写入本地配置，并在相机连接时自动应用；已连接的相机也会立即尝试应用。
          </p>
        </div>

        {/* Confidence */}
        <div className="space-y-4">
          <div className="flex justify-between">
            <label className="text-sm font-medium text-gray-300">置信度阈值 (Confidence)</label>
            <span className="text-indigo-400 font-mono font-bold">{(conf * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.05" max="0.95" step="0.05"
            value={conf}
            onChange={e => setConf(parseFloat(e.target.value))}
            className="w-full h-2 bg-black/40 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
          <p className="text-xs text-gray-500">
            较低的阈值会检测到更多目标但可能包含误报，较高的阈值只保留最可信的结果。
          </p>
        </div>

        {/* Log Interval */}
        <div className="space-y-4">
          <div className="flex justify-between">
            <label className="text-sm font-medium text-gray-300">实时告警冷却时间 (Log Interval)</label>
            <span className="text-indigo-400 font-mono font-bold">{logInterval} 秒</span>
          </div>
          <input
            type="range"
            min="1" max="60" step="1"
            value={logInterval}
            onChange={e => setLogInterval(parseInt(e.target.value))}
            className="w-full h-2 bg-black/40 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
          <p className="text-xs text-gray-500">
            控制实时检测中异常记录的写入频率，防止日志刷屏。设置为 10s 表示每 10 秒最多记录一次异常。
          </p>
        </div>

        {/* Resolution */}
        <div className="space-y-4">
          <label className="text-sm font-medium text-gray-300">推理分辨率 (Inference Resolution)</label>
          <div className="grid grid-cols-3 gap-3">
            {[320, 640, 1280].map(size => (
              <button
                key={size}
                onClick={() => setImgsz(size)}
                className={clsx(
                  "px-4 py-3 rounded-lg border text-sm font-medium transition-all",
                  imgsz === size
                    ? "bg-indigo-600 border-indigo-500 text-white shadow-[0_0_15px_rgba(79,70,229,0.3)]"
                    : "bg-white/5 border-white/5 text-gray-400 hover:bg-white/10"
                )}
              >
                {size} x {size}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500">
            分辨率越高检测越精准（尤其是小目标），但会显著增加推理耗时。建议使用 640。
          </p>
        </div>

        <div className="pt-4 border-t border-[var(--border)] flex justify-end">
          <button
            onClick={saveSettings}
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "保存中..." : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
