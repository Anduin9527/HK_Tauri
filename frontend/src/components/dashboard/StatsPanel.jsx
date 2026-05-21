import React from 'react';
import { Link, Cpu, Activity } from 'lucide-react';

export default function StatsPanel({ stats, slotMapping, cameraFps }) {
  // Count connected cameras
  const connectedCount = Object.values(slotMapping).filter(Boolean).length;

  // Calculate average FPS for connected cameras
  let totalFps = 0;
  let activeCamCount = 0;
  Object.keys(slotMapping).forEach((slotId) => {
    if (slotMapping[slotId]) {
      const fpsInfo = cameraFps?.[slotId];
      if (fpsInfo) {
        const camFps = Number(fpsInfo.camera_fps ?? fpsInfo.capture_fps ?? fpsInfo.stream_fps ?? 0);
        totalFps += camFps;
        activeCamCount++;
      }
    }
  });
  const avgFps = activeCamCount > 0 ? (totalFps / activeCamCount).toFixed(1) : "0.0";

  return (
    <div className="grid grid-cols-3 gap-3 shrink-0">
      {/* Connected Cameras Card */}
      <div className="glass-card p-3 rounded flex flex-col justify-between hover-lift">
        <div className="flex items-center justify-between text-gray-500 mb-1 font-semibold">
          <span className="text-[9px] uppercase tracking-wider">通道连接数</span>
          <Link size={12} className="text-blue-500" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-xl font-bold font-mono text-[var(--text-main)]">{connectedCount}</span>
          <span className="text-[10px] font-mono text-[var(--text-muted)]">/ 4 CH</span>
        </div>
      </div>

      {/* Average FPS Card */}
      <div className="glass-card p-3 rounded flex flex-col justify-between hover-lift">
        <div className="flex items-center justify-between text-gray-500 mb-1 font-semibold">
          <span className="text-[9px] uppercase tracking-wider">传感器帧率</span>
          <Cpu size={12} className="text-emerald-500" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-xl font-bold font-mono text-[var(--text-main)]">{avgFps}</span>
          <span className="text-[10px] font-mono text-[var(--text-muted)]">FPS</span>
        </div>
      </div>

      {/* CPU Usage Card */}
      <div className="glass-card p-3 rounded flex flex-col justify-between hover-lift">
        <div className="flex items-center justify-between text-gray-500 mb-1 font-semibold">
          <span className="text-[9px] uppercase tracking-wider">主机CPU负载</span>
          <Activity size={12} className="text-blue-500" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-xl font-bold font-mono text-[var(--text-main)]">{stats.cpu ?? 0}</span>
          <span className="text-[10px] font-mono text-[var(--text-muted)]">%</span>
        </div>
      </div>
    </div>
  );
}
