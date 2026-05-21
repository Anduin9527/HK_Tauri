import React from 'react';
import VideoFeed from '../VideoFeed';
import { Link, Link2Off } from 'lucide-react';
import clsx from 'clsx';

export default function VideoGrid({
  streaming,
  slotMapping,
  maximizedSlot,
  setMaximizedSlot,
  cameraFps,
  autoInference,
  availableCameras,
  loadingCameras,
  globalBusy,
  slotBusy,
  onConnectCamera,
  onDisconnectCamera,
  BACKEND_URL,
}) {
  return (
    <div
      className={clsx(
        "grid gap-3 flex-1 min-h-[500px]",
        maximizedSlot !== null ? "grid-cols-1 grid-rows-1" : "grid-cols-2 grid-rows-2"
      )}
    >
      {[0, 1, 2, 3].map((slotId) => {
        // If a slot is maximized, hide all other slots
        if (maximizedSlot !== null && maximizedSlot !== slotId) return null;

        const isConnected = streaming && !!slotMapping[slotId];
        const isBusy = globalBusy || slotBusy?.[slotId];

        return (
          <div
            key={slotId}
            className={clsx(
              "relative w-full h-full min-h-0 border border-[var(--border)] rounded overflow-hidden",
              !isConnected && "unconnected-bg"
            )}
          >
            {/* Slot Header Controls */}
            <div className="absolute top-2 left-2 z-20 flex items-center gap-1.5">
              <div className="px-2 py-0.5 bg-black/80 rounded border border-white/10 text-[9px] font-bold font-mono text-white/70">
                CH-{slotId + 1}
              </div>

              {/* Camera Selector */}
              <div className="relative flex items-center">
                {!slotMapping[slotId] ? (
                  <div className="relative">
                    <select
                      className="h-5 pl-2 pr-5 bg-[#1b1d28] border border-[var(--border)] text-[9px] font-semibold text-[var(--text-muted)] hover:text-white rounded cursor-pointer transition-all appearance-none outline-none"
                      onChange={(e) => {
                        if (e.target.value !== "") onConnectCamera(slotId, e.target.value);
                      }}
                      value=""
                      disabled={loadingCameras || isBusy}
                    >
                      <option value="" disabled>UNBOUND (点击绑定相机)...</option>
                      {availableCameras.map((cam) => (
                        <option key={cam.index} value={cam.index} className="bg-[var(--bg-dark)] text-white">
                          {cam.name} ({cam.type})
                        </option>
                      ))}
                    </select>
                    <div className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500">
                      <Link size={8} />
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <span className="h-5 px-2 flex items-center bg-blue-600/10 border border-blue-500/20 text-[9px] font-bold font-mono text-blue-400 rounded">
                      {slotMapping[slotId].name}
                    </span>
                    <button
                      onClick={() => onDisconnectCamera(slotId)}
                      className="h-5 w-5 flex items-center justify-center bg-black/60 hover:bg-red-500/80 border border-white/5 rounded text-white transition-colors cursor-pointer"
                      title="断开设备连接"
                      disabled={isBusy}
                    >
                      <Link2Off size={10} />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Video Stream Component */}
            <VideoFeed
              streamUrl={streaming && slotMapping[slotId] ? `${BACKEND_URL}/video_feed/${slotId}` : ""}
              isConnected={isConnected}
              onMaximize={() => setMaximizedSlot(maximizedSlot === slotId ? null : slotId)}
              isMaximized={maximizedSlot === slotId}
              fps={cameraFps?.[slotId]}
              autoInference={autoInference}
            />
          </div>
        );
      })}
    </div>
  );
}
