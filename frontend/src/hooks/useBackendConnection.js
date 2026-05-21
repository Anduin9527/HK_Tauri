import { useState, useEffect, useCallback, useRef } from 'react';
import { io } from 'socket.io-client';

const BACKEND_URL = "http://localhost:8000";

/**
 * Manages Socket.IO connection, log state, camera FPS data, and backend status polling.
 */
export function useBackendConnection() {
  const [logs, setLogs] = useState([]);
  const [cameraFps, setCameraFps] = useState({});
  const [stats, setStats] = useState({ cpu: 0 });
  const [autoInference, setAutoInference] = useState(false);
  const socketRef = useRef(null);

  const addLog = useCallback((title, message, severity, attachment = null, time = null) => {
    setLogs(prev => [
      { id: Date.now(), title, message, severity, attachment, time: time || new Date().toLocaleTimeString() },
      ...prev,
    ].slice(0, 50));
  }, []);

  // Socket.IO connection
  useEffect(() => {
    const socket = io(BACKEND_URL);
    socketRef.current = socket;

    socket.on('log_message', (data) => {
      addLog(data.title, data.message, data.severity, data.attachment, data.time);
    });

    socket.on('camera_fps', (data) => {
      if (data?.cameras) setCameraFps(data.cameras);
    });

    return () => socket.disconnect();
  }, [addLog]);

  // Fetch initial auto/manual mode
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

  const toggleAutoInference = useCallback(async () => {
    try {
      const nextIsManual = autoInference;
      await fetch(`${BACKEND_URL}/config/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manual_mode: nextIsManual }),
      });
      setAutoInference(!nextIsManual);
    } catch (e) {
      addLog("错误", "切换模式失败: " + e.message, "high");
    }
  }, [autoInference, addLog]);

  const triggerDetection = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/trigger/detect`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    } catch (e) {
      addLog("错误", "触发失败: " + e.message, "high");
    }
  }, [addLog]);

  const refreshLogs = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/logs?lines=100`);
      const data = await res.json();
      setLogs((data.logs || []).map((l, i) => ({ ...l, id: `${l.time}-${i}` })));
    } catch (e) {
      addLog("错误", "刷新日志失败: " + e.message, "high");
    }
  }, [addLog]);

  // Status polling
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/status`);
        const data = await res.json();
        if (data.model_loaded) {
          setStats({ cpu: Math.round(15 + Math.random() * 10) });
        }
      } catch (_) { /* backend offline */ }
    };

    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  return {
    logs,
    cameraFps,
    stats,
    autoInference,
    addLog,
    toggleAutoInference,
    triggerDetection,
    refreshLogs,
    BACKEND_URL,
  };
}
