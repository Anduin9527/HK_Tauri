import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import clsx from 'clsx';

export default function CameraParamsCard({ slotKey, params, loading, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const isAuto = params?.exposure_mode === "auto";

  const handleToggleMode = (e) => {
    e.stopPropagation(); // Prevent toggling accordion
    const nextMode = isAuto ? "manual" : "auto";
    onChange({
      ...params,
      exposure_mode: nextMode,
    });
  };

  const handleExposureChange = (e) => {
    const val = parseFloat(e.target.value);
    onChange({
      ...params,
      exposure_time_us: Number.isFinite(val) ? val : 50000,
    });
  };

  const handleGainChange = (e) => {
    const val = parseFloat(e.target.value);
    onChange({
      ...params,
      gain_db: Number.isFinite(val) ? val : 0,
    });
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded overflow-hidden">
      {/* Header (Accordion Toggle) */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500 font-mono">CH-{Number(slotKey) + 1}</span>
          <span className="text-xs font-bold text-[var(--text-main)]">相机参数通道</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Exposure Mode Pill */}
          <button
            onClick={handleToggleMode}
            disabled={loading}
            className={clsx(
              "px-2.5 py-0.5 rounded text-[9px] font-bold border transition-all cursor-pointer",
              isAuto
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-black/20 text-[var(--text-muted)] border-[var(--border)] hover:text-white"
            )}
          >
            {isAuto ? "AUTO EXP" : "MANUAL EXP"}
          </button>
          
          {/* Accordion Arrow */}
          <div className="text-gray-500">
            {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </div>

      {/* Accordion Body */}
      <div
        className="accordion-content"
        data-open={isOpen ? "true" : "false"}
      >
        <div className="p-3 border-t border-[var(--border)] bg-black/10 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {/* Exposure Time */}
            <div className="space-y-1">
              <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">
                曝光时间 (µs)
              </label>
              <input
                type="number"
                min="1"
                step="100"
                value={params?.exposure_time_us ?? 50000}
                onChange={handleExposureChange}
                className={clsx(
                  "w-full bg-black/20 border border-[var(--border)] rounded px-2 py-1 text-xs font-mono text-[var(--text-main)] outline-none focus:border-blue-500 transition-all",
                  isAuto && "opacity-40 cursor-not-allowed border-[var(--border)]/50"
                )}
                disabled={loading || isAuto}
              />
            </div>

            {/* Gain */}
            <div className="space-y-1">
              <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">
                增益值 (dB)
              </label>
              <input
                type="number"
                step="0.1"
                value={params?.gain_db ?? 0}
                onChange={handleGainChange}
                className="w-full bg-black/20 border border-[var(--border)] rounded px-2 py-1 text-xs font-mono text-[var(--text-main)] outline-none focus:border-blue-500 transition-all"
                disabled={loading}
              />
            </div>
          </div>

          {isAuto && (
            <p className="text-[9px] text-emerald-400/80 italic">
              * 提示：已启用自动曝光。相机硬件驱动程序将根据传感器光强反馈自动计算所需曝光时长。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
