import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';

const BACKEND_URL = "http://localhost:8000";

/**
 * Manages settings state: model selection, camera params, confidence, resolution, log interval.
 */
export function useSettings(addLog) {
  const [conf, setConf] = useState(0.25);
  const [imgsz, setImgsz] = useState(640);
  const [logInterval, setLogInterval] = useState(10);
  const [modelType, setModelType] = useState('auto');
  const [modelName, setModelName] = useState('yolo26s');
  const [availableModels, setAvailableModels] = useState([]);
  const [cameraParams, setCameraParams] = useState({
    "0": { exposure_time_us: 50000, gain_db: 0, exposure_mode: "manual" },
    "1": { exposure_time_us: 50000, gain_db: 0, exposure_mode: "manual" },
    "2": { exposure_time_us: 50000, gain_db: 0, exposure_mode: "manual" },
    "3": { exposure_time_us: 50000, gain_db: 0, exposure_mode: "manual" },
  });
  const [loading, setLoading] = useState(false);

  // Load models list and settings on mount
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

  const applyModelSelection = useCallback(async (nextName, nextType) => {
    setLoading(true);
    setModelName(nextName);
    setModelType(nextType);
    try {
      const res = await fetch(`${BACKEND_URL}/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conf, imgsz, log_interval: logInterval, model_type: nextType, model_name: nextName, camera_params: cameraParams }),
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
  }, [conf, imgsz, logInterval, cameraParams, addLog]);

  const saveSettings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/config/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conf, imgsz, log_interval: logInterval, model_type: modelType, model_name: modelName, camera_params: cameraParams }),
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
  }, [conf, imgsz, logInterval, modelType, modelName, cameraParams, addLog]);

  const openDataFolder = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/paths`);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`路径接口异常: ${res.status} ${text || res.statusText}`);
      }
      const data = await res.json();
      const target = data?.history_dir || data?.data_dir;
      if (!target) throw new Error("未返回有效路径");
      await invoke('open_path', { path: target });
      addLog("系统", "已打开数据文件夹", "info");
    } catch (e) {
      addLog("错误", "无法打开文件夹: " + (e?.message || String(e)), "high");
    }
  }, [addLog]);

  return {
    conf, setConf,
    imgsz, setImgsz,
    logInterval, setLogInterval,
    modelType, modelName,
    availableModels,
    cameraParams, setCameraParams,
    loading,
    applyModelSelection,
    saveSettings,
    openDataFolder,
  };
}
