import React from 'react';
import { Sliders, Eye, Clock, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';

export default function DetectionConfig({
  conf,
  setConf,
  imgsz,
  setImgsz,
  logInterval,
  setLogInterval,
}) {
  return (
    <div className="space-y-4 bg-[var(--bg-card)] p-3.5 rounded border border-[var(--border)]">
      {/* Title */}
      <div className="flex items-center gap-1.5 text-blue-500">
        <Sliders size={14} />
        <h4 className="text-xs font-bold text-[var(--text-main)]">缺陷算法与检测参数</h4>
      </div>

      {/* Confidence Threshold */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-baseline">
          <div className="flex items-center gap-1 text-[11px] text-[var(--text-main)] font-semibold">
            <Eye size={12} className="text-gray-400" />
            <span>置信度阈值 (Confidence)</span>
          </div>
          <span className="text-xs font-mono font-bold text-blue-400">
            {Math.round(conf * 100)}%
          </span>
        </div>
        <input
          type="range"
          min="0.05"
          max="0.95"
          step="0.05"
          value={conf}
          onChange={(e) => setConf(parseFloat(e.target.value))}
          className="w-full h-1 bg-black/20 rounded cursor-pointer accent-blue-600"
        />
        <p className="text-[9px] text-[var(--text-muted)]">
          控制 AI 预测输出过滤门槛。过滤值越低，漏检越少，但可能增加误报率。
        </p>
      </div>

      {/* Log Cool Down Interval */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-baseline">
          <div className="flex items-center gap-1 text-[11px] text-[var(--text-main)] font-semibold">
            <Clock size={12} className="text-gray-400" />
            <span>实时告警冷却时间 (Log Interval)</span>
          </div>
          <span className="text-xs font-mono font-bold text-blue-400">
            {logInterval} 秒
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="60"
          step="1"
          value={logInterval}
          onChange={(e) => setLogInterval(parseInt(e.target.value))}
          className="w-full h-1 bg-black/20 rounded cursor-pointer accent-blue-600"
        />
        <p className="text-[9px] text-[var(--text-muted)]">
          避免针对同一相机持续发生的异常缺陷报警刷屏。同一通道至少在冷却时间过后才会再次推送告警。
        </p>
      </div>

      {/* Resolution Selector */}
      <div className="space-y-2">
        <div className="flex items-center gap-1 text-[11px] text-[var(--text-main)] font-semibold">
          <ShieldAlert size={12} className="text-gray-400" />
          <span>输入推理分辨率 (Resolution)</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[320, 640, 1280].map((res) => {
            const isSelected = imgsz === res;
            return (
              <button
                key={res}
                type="button"
                onClick={() => setImgsz(res)}
                className={clsx(
                  "py-1.5 rounded text-xs font-mono font-bold border transition-all cursor-pointer",
                  isSelected
                    ? "bg-blue-600 text-white border-blue-500"
                    : "bg-black/20 text-gray-400 border-[var(--border)] hover:text-white"
                )}
              >
                {res} × {res}
              </button>
            );
          })}
        </div>
        <p className="text-[9px] text-[var(--text-muted)] leading-relaxed">
          改变图片缩放尺寸。640 为标准 YOLO 推荐尺寸。1280 提供高精度，但推理耗时增加。
        </p>
      </div>
    </div>
  );
}
