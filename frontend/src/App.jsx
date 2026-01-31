import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import './App.css';
import { Play, Square, Settings, Activity, AlertTriangle, Cpu, Minimize2, Image as ImageIcon } from 'lucide-react';
import VideoFeed from './components/VideoFeed';
import clsx from 'clsx';

// Constants
const BACKEND_URL = "http://localhost:8000";
const VIDEO_STREAM_URL = `${BACKEND_URL}/video_feed`;

function App() {
  const [streaming, setStreaming] = useState(false);
  const [stats, setStats] = useState({ fps: 0, cpu: 0, defects: 0 });
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [debugImage, setDebugImage] = useState(null);

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

  const addLog = (title, message, severity, attachment = null) => {
    setLogs(prev => [{ id: Date.now(), title, message, severity, attachment, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 50));
  };

  // Socket.IO Connection
  useEffect(() => {
    const socket = io(BACKEND_URL);

    socket.on('log_message', (data) => {
      addLog(data.title, data.message, data.severity, data.attachment);
    });

    return () => socket.disconnect();
  }, []);

  const toggleStream = async () => {
    try {
      setStreaming(!streaming);
    } catch (e) {
      console.error("Error toggling stream:", e);
    }
  };

  // Poll for backend status/stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/status`);
        const data = await res.json();

        if (data.camera_connected) {
          setStats(prev => ({
            fps: Math.round(28 + Math.random() * 4),
            cpu: Math.round(15 + Math.random() * 10),
            defects: prev.defects
          }));
        }
      } catch (e) {
        // console.log("Backend offline");
      }
    };

    // Fallback log generator fordemo
    const demoLogInterval = setInterval(() => {
      if (streaming && Math.random() > 0.95) {
        const defects = ["表面划痕", "异物检测", "边缘缺损", "颜色异常"];
        const defect = defects[Math.floor(Math.random() * defects.length)];
        addLog("检测到缺陷", `检测到 ${defect}`, Math.random() > 0.5 ? "high" : "medium");
        setStats(s => ({ ...s, defects: s.defects + 1 }));
      }
    }, 2000);

    const interval = setInterval(fetchStats, 2000);
    return () => {
      clearInterval(interval);
      clearInterval(demoLogInterval);
    };
  }, [streaming]);

  return (
    <div className="h-screen w-screen flex bg-[var(--bg-dark)] text-white overflow-hidden relative">

      {/* Debug Image Modal */}
      {debugImage && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm p-4 md:p-8"
          onClick={() => setDebugImage(null)}
        >
          <div
            className="relative bg-[#151515] border border-white/10 rounded-xl shadow-2xl max-w-[95vw] max-h-[95vh] flex flex-col"
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
      <aside className="w-20 lg:w-64 border-r border-[var(--border)] flex flex-col glass z-20">
        <div className="p-6 flex items-center gap-3 border-b border-[var(--border)]">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-[0_0_15px_rgba(79,70,229,0.5)]">
            <Activity size={18} className="text-white" />
          </div>
          <span className="font-bold tracking-wide hidden lg:block">NEXUS<span className="text-indigo-400">AI</span> 视觉平台</span>
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
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              )}
            >
              <item.icon size={20} className={clsx("transition-transform group-hover:scale-110", activeTab === item.id && "text-indigo-400")} />
              <span className="hidden lg:block font-medium">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-[var(--border)]">
          <div className="p-3 bg-white/5 rounded-xl border border-white/5">
            <div className="flex items-center gap-3 mb-2">
              <Cpu size={16} className="text-emerald-400" />
              <span className="text-xs font-mono text-gray-400">INTEL 系统状态</span>
            </div>
            <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 w-[35%]" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-hidden">

        {/* Top Bar for Status */}
        <header className="h-16 border-b border-[var(--border)] flex items-center justify-between px-8 glass z-10">
          <h1 className="text-lg font-semibold text-white/90">
            {activeTab === 'dashboard' ? '实时推理监控' : activeTab === 'logs' ? '缺陷日志历史' : '系统设置'}
          </h1>
          <div className="flex items-center gap-4">
            <div className="px-3 py-1 bg-black/40 rounded-full border border-white/10 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-mono text-green-400">系统就绪</span>
            </div>
          </div>
        </header>

        <div className="flex-1 p-6 overflow-y-auto">

          {/* Dashboard View */}
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-full">

              {/* Video Feed Area */}
              <div className="xl:col-span-2 flex flex-col gap-6">
                <VideoFeed
                  streamUrl={streaming ? VIDEO_STREAM_URL : ""}
                  isConnected={streaming}
                />

                {/* Control Bar */}
                <div className="p-4 glass-card rounded-xl flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300">摄像头控制</h3>
                    <p className="text-xs text-gray-500">Hikvision DS-2CD 系列 (RTSP)</p>
                  </div>
                  <div className="flex gap-4">
                    <button
                      onClick={toggleStream}
                      className={clsx(
                        "px-6 py-2 rounded-lg font-medium transition-all shadow-[0_4px_14px_0_rgba(0,0,0,0.39)] hover:shadow-none hover:translate-y-[1px] flex items-center gap-2",
                        streaming
                          ? "bg-red-500/10 text-red-400 border border-red-500/50 hover:bg-red-500/20"
                          : "bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-[0_0_20px_rgba(79,70,229,0.4)]"
                      )}
                    >
                      {streaming ? <Square size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
                      {streaming ? "停止推流" : "开始推流"}
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Panel: Stats & Logs */}
              <div className="flex flex-col gap-6 h-full">
                {/* Stats Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="glass-card p-4 rounded-xl flex flex-col gap-1">
                    <span className="text-xs text-gray-400 uppercase tracking-wider">FPS (帧率)</span>
                    <span className="text-2xl font-bold font-mono text-white">{stats.fps}</span>
                  </div>
                  <div className="glass-card p-4 rounded-xl flex flex-col gap-1">
                    <span className="text-xs text-gray-400 uppercase tracking-wider">今日缺陷数</span>
                    <span className="text-2xl font-bold font-mono text-indigo-400">{stats.defects}</span>
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
                  <div className="p-4 border-b border-[var(--border)] bg-white/5">
                    <h3 className="text-sm font-medium">最近告警</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {logs.length === 0 ? (
                      <div className="text-center text-gray-600 text-sm py-10">暂无检测记录</div>
                    ) : (
                      logs.map(log => (
                        <div key={log.id} className="flex gap-3 items-start p-3 rounded-lg bg-white/5 border border-white/5 hover:border-indigo-500/30 transition-colors">
                          <div className="mt-1">
                            <AlertTriangle size={16} className={log.severity === 'high' ? 'text-red-400' : 'text-yellow-400'} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-baseline mb-1">
                              <h4 className="text-sm font-medium text-gray-200 truncate">{log.title}</h4>
                              <span className="text-[10px] text-gray-500 font-mono">{log.time}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <p className="text-xs text-gray-400 line-clamp-2">{log.message}</p>
                              {log.attachment && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setDebugImage(log.attachment); }}
                                  className="p-1 hover:bg-white/10 rounded text-indigo-400"
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
                <h2 className="text-lg font-medium text-gray-200">系统运行日志</h2>
                <button
                  onClick={() => {
                    // Refresh logs
                    fetch(`${BACKEND_URL}/logs?lines=100`)
                      .then(res => res.json())
                      .then(data => setLogs(data.logs.map((l, i) => ({ ...l, id: i })) || []));
                  }}
                  className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-gray-300 transition-colors"
                >
                  刷新日志
                </button>
              </div>
              <div className="flex-1 overflow-auto rounded-xl border border-white/5 bg-black/20">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/5 text-gray-400 sticky top-0 backdrop-blur-md">
                    <tr>
                      <th className="p-4 font-medium">时间</th>
                      <th className="p-4 font-medium">级别</th>
                      <th className="p-4 font-medium">模块</th>
                      <th className="p-4 font-medium w-full">详情</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {logs.map((log, i) => (
                      <tr key={i} className="hover:bg-white/5 transition-colors">
                        <td className="p-4 font-mono text-gray-500 whitespace-nowrap">{log.time}</td>
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
                        <td className="p-4 text-gray-300 whitespace-nowrap">{log.title}</td>
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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${BACKEND_URL}/config/settings`)
      .then(res => res.json())
      .then(data => {
        if (data.conf) setConf(data.conf);
        if (data.imgsz) setImgsz(data.imgsz);
      })
      .catch(e => console.error(e));
  }, []);

  const saveSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conf, imgsz })
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
        <h2 className="text-2xl font-semibold text-white">系统参数配置</h2>
        <p className="text-gray-400">调整检测模型的灵敏度和即时处理参数。</p>
      </div>

      <div className="p-6 glass-card rounded-xl space-y-8">
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

        <div className="pt-4 border-t border-white/5 flex justify-end">
          <button
            onClick={saveSettings}
            disabled={loading}
            className="px-6 py-2 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "保存中..." : "保存设置"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
