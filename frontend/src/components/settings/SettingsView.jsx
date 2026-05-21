import React from 'react';
import { FolderOpen, Save, Settings, Loader } from 'lucide-react';
import ModelSelector from './ModelSelector';
import CameraParamsCard from './CameraParamsCard';
import DetectionConfig from './DetectionConfig';
import clsx from 'clsx';

export default function SettingsView({ settings }) {
  const {
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
  } = settings;

  const handleCameraParamChange = (slotKey, updatedSlotParams) => {
    setCameraParams((prev) => ({
      ...prev,
      [slotKey]: {
        ...prev[slotKey],
        ...updatedSlotParams,
      },
    }));
  };

  return (
    <div className="max-w-xl mx-auto py-4 space-y-4 min-h-0 page-enter">
      {/* Title */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="p-1.5 bg-blue-600/10 border border-blue-500/20 text-blue-400 rounded">
          <Settings size={16} />
        </div>
        <div>
          <h2 className="text-sm font-bold text-[var(--text-main)]">系统参数配置</h2>
          <p className="text-[10px] text-[var(--text-muted)]">管理深度学习网络参数、外部相机硬件设定及日志路径</p>
        </div>
      </div>

      {/* Main Container Card */}
      <div className="glass-card rounded p-4 space-y-4">
        {/* Open Folder Section */}
        <div className="p-3 rounded bg-blue-600/5 border border-blue-500/10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="space-y-0.5">
            <h4 className="text-xs font-bold text-blue-400">本地缺陷数据存储</h4>
            <p className="text-[9px] text-[var(--text-muted)] leading-relaxed">
              所有相机的实时抓拍原图、缺陷标注检测图及检测历史日志均存储于该位置下。
            </p>
          </div>
          <button
            onClick={openDataFolder}
            className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition-all shrink-0 cursor-pointer"
          >
            <FolderOpen size={12} />
            <span>打开存储文件夹</span>
          </button>
        </div>

        {/* Model Selector */}
        <ModelSelector
          modelName={modelName}
          modelType={modelType}
          availableModels={availableModels}
          loading={loading}
          onApplyModelSelection={applyModelSelection}
        />

        {/* Camera Params Accordion Group */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-[var(--text-main)]">相机通道物理参数 (4CH)</h4>
            <span className="text-[9px] font-mono text-[var(--text-muted)]">点击各通道展开调节参数</span>
          </div>

          <div className="space-y-1.5">
            {["0", "1", "2", "3"].map((slotKey) => (
              <CameraParamsCard
                key={slotKey}
                slotKey={slotKey}
                params={cameraParams?.[slotKey]}
                loading={loading}
                onChange={(updatedParams) => handleCameraParamChange(slotKey, updatedParams)}
              />
            ))}
          </div>
        </div>

        {/* Algorithm Settings */}
        <DetectionConfig
          conf={conf}
          setConf={setConf}
          imgsz={imgsz}
          setImgsz={setImgsz}
          logInterval={logInterval}
          setLogInterval={setLogInterval}
        />

        {/* Action Save Button */}
        <div className="pt-3 border-t border-[var(--border)] flex justify-end">
          <button
            onClick={saveSettings}
            disabled={loading}
            className={clsx(
              "px-5 py-2 rounded font-bold text-xs text-white transition-all flex items-center gap-1.5 cursor-pointer",
              loading
                ? "bg-blue-600/50 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            )}
          >
            {loading ? (
              <>
                <Loader size={12} className="animate-spin" />
                <span>保存配置中...</span>
              </>
            ) : (
              <>
                <Save size={12} />
                <span>保存参数设置</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
