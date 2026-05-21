import React, { useRef, useState } from 'react';
import { Play, Square, RefreshCw, Zap, Camera, Image as ImageIcon, Loader } from 'lucide-react';
import clsx from 'clsx';

export default function ControlBar({
  streaming,
  autoInference,
  globalBusy,
  slotBusy,
  loadingCameras,
  onToggleStream,
  onToggleAutoInference,
  onTriggerDetection,
  onRefreshCameras,
  onUploadImage,
  BACKEND_URL,
  addLog,
}) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);

    try {
      addLog("调试", "正在上传本地测试图片进行分析...", "medium");
      const res = await fetch(`${BACKEND_URL}/predict/image`, {
        method: 'POST',
        body: formData,
      });

      if (res.status === 400) {
        const data = await res.json();
        addLog("操作失败", data.error || "推理请求失败", "high");
        alert(data.error || "请求失败");
        return;
      }

      if (res.ok) {
        const data = await res.json();
        if (data.image_url) {
          addLog("调试", "图片分析成功", "medium", data.image_url);
          if (onUploadImage) {
            onUploadImage(data.image_url);
          }
        } else {
          addLog("错误", "后端返回的图片地址为空", "high");
        }
      } else {
        addLog("错误", "上传失败: " + res.statusText, "high");
      }
    } catch (err) {
      console.error(err);
      addLog("错误", "连接推理服务器失败: " + err.message, "high");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const triggerUploadClick = () => {
    if (uploading) return;
    fileInputRef.current?.click();
  };

  const isBusy = globalBusy || Object.values(slotBusy || {}).some(Boolean);

  return (
    <div className="p-3.5 bg-[var(--bg-card)] border border-[var(--border)] rounded flex items-center justify-between shrink-0 hover-lift">
      {/* Left side: Titles + Refresh */}
      <div className="flex items-center gap-3">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">系统控制中心</h3>
          <p className="text-[9px] text-[var(--text-muted)] font-mono">HIKVISION CAPTURE & INFERENCE RUNTIME</p>
        </div>
        <button
          onClick={onRefreshCameras}
          disabled={loadingCameras || isBusy}
          className="p-1.5 rounded bg-white/5 border border-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          title="重新扫描相机硬件"
        >
          <RefreshCw size={14} className={clsx(loadingCameras && "animate-spin")} />
        </button>
      </div>

      {/* Right side: Button Controls */}
      <div className="flex items-center gap-2">
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept="image/*"
          onChange={handleFileChange}
        />

        {/* Upload Image Button */}
        <button
          onClick={triggerUploadClick}
          disabled={uploading}
          className={clsx(
            "p-2 rounded border text-gray-400 hover:text-white transition-all cursor-pointer",
            uploading
              ? "bg-blue-600/10 border-blue-500/30 text-blue-400"
              : "bg-white/5 border-white/5 hover:bg-white/10"
          )}
          title="上传图片文件调试"
        >
          {uploading ? <Loader size={14} className="animate-spin" /> : <ImageIcon size={14} />}
        </button>

        {/* Mode Toggle (Auto / Manual) */}
        <button
          onClick={onToggleAutoInference}
          className={clsx(
            "px-3 py-1.5 rounded font-bold border text-[10px] transition-all flex items-center gap-1.5 cursor-pointer",
            autoInference
              ? "bg-blue-600/10 text-blue-400 border-blue-500/30"
              : "bg-white/5 text-gray-400 border-white/5 hover:bg-white/10"
          )}
        >
          <Zap size={12} className={clsx(autoInference && "fill-current text-blue-400")} />
          <span>{autoInference ? "自动推理模式" : "手动单步模式"}</span>
        </button>

        {/* Manual Trigger (Only in manual mode) */}
        {!autoInference && (
          <button
            onClick={onTriggerDetection}
            disabled={!streaming || globalBusy}
            className="px-3.5 py-1.5 rounded font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition-all flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed text-[10px] cursor-pointer"
            title="手动触发抓拍检测"
          >
            <Camera size={12} />
            <span>单次检测</span>
          </button>
        )}

        {/* Divider */}
        <div className="w-px h-5 bg-white/10 mx-1" />

        {/* Start / Stop Streaming */}
        <button
          onClick={onToggleStream}
          disabled={globalBusy}
          className={clsx(
            "px-4 py-1.5 rounded font-bold transition-all flex items-center gap-1.5 text-[10px] cursor-pointer",
            streaming
              ? "bg-red-600/10 text-red-400 border border-red-500/20 hover:bg-red-600/20"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          )}
        >
          {streaming ? (
            <>
              <Square size={12} className="fill-current" />
              <span>关闭监控推流</span>
            </>
          ) : (
            <>
              <Play size={12} className="fill-current" />
              <span>启动全网推流</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
