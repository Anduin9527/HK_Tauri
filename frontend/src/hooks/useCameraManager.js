import { useState, useEffect, useCallback } from 'react';

const BACKEND_URL = "http://localhost:8000";

/**
 * Manages camera discovery, slot mapping, connect/disconnect operations.
 */
export function useCameraManager(addLog) {
  const [availableCameras, setAvailableCameras] = useState([]);
  const [slotMapping, setSlotMapping] = useState({ 0: null, 1: null, 2: null, 3: null });
  const [loadingCameras, setLoadingCameras] = useState(false);
  const [slotBusy, setSlotBusy] = useState({ 0: false, 1: false, 2: false, 3: false });
  const [globalBusy, setGlobalBusy] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [maximizedSlot, setMaximizedSlot] = useState(null);

  const refreshCameras = useCallback(async () => {
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
  }, [addLog]);

  // Initial load
  useEffect(() => {
    refreshCameras();
  }, [refreshCameras]);

  const connectCamera = useCallback(async (slotId, cameraIndex) => {
    if (globalBusy || slotBusy?.[slotId]) return;
    setSlotBusy(prev => ({ ...prev, [slotId]: true }));
    try {
      const res = await fetch(`${BACKEND_URL}/cameras/${slotId}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_index: parseInt(cameraIndex) }),
      });

      if (res.ok) {
        const cam = availableCameras.find(c => c.index === parseInt(cameraIndex));
        setSlotMapping(prev => ({
          ...prev,
          [slotId]: cam || { index: cameraIndex, name: `Camera ${cameraIndex}` },
        }));
        addLog("系统", `Slot ${slotId} 已绑定设备: ${cam?.name || cameraIndex}`, "info");
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
  }, [globalBusy, slotBusy, availableCameras, streaming, addLog]);

  const disconnectCamera = useCallback(async (slotId) => {
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
  }, [globalBusy, slotBusy, addLog]);

  const disconnectAllCameras = useCallback(async () => {
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
      setSlotMapping({ 0: null, 1: null, 2: null, 3: null });
      setMaximizedSlot(null);
      setStreaming(false);
      addLog("系统", "已断开所有摄像头连接", "info");
    } catch (e) {
      addLog("错误", "断开所有摄像头失败: " + e.message, "high");
    } finally {
      setGlobalBusy(false);
    }
  }, [globalBusy, addLog]);

  const toggleStream = useCallback(async () => {
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
  }, [globalBusy, streaming, slotMapping, disconnectAllCameras, addLog]);

  return {
    availableCameras,
    slotMapping,
    loadingCameras,
    slotBusy,
    globalBusy,
    streaming,
    maximizedSlot,
    setMaximizedSlot,
    refreshCameras,
    connectCamera,
    disconnectCamera,
    disconnectAllCameras,
    toggleStream,
    BACKEND_URL,
  };
}
