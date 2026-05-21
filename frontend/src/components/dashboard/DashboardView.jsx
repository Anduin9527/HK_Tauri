import React from 'react';
import VideoGrid from './VideoGrid';
import ControlBar from './ControlBar';
import StatsPanel from './StatsPanel';
import AlertFeed from './AlertFeed';

export default function DashboardView({
  streaming,
  slotMapping,
  maximizedSlot,
  setMaximizedSlot,
  cameraFps,
  autoInference,
  stats,
  logs,
  availableCameras,
  loadingCameras,
  globalBusy,
  slotBusy,
  onConnectCamera,
  onDisconnectCamera,
  onToggleStream,
  onToggleAutoInference,
  onTriggerDetection,
  onRefreshCameras,
  onViewImage,
  addLog,
  BACKEND_URL,
}) {
  return (
    <div className="flex flex-col xl:flex-row gap-3 h-full min-h-0 page-enter">
      {/* Left Column: Video Grid + Controls */}
      <div className="flex-1 flex flex-col gap-3 min-h-0 min-w-0">
        <VideoGrid
          streaming={streaming}
          slotMapping={slotMapping}
          maximizedSlot={maximizedSlot}
          setMaximizedSlot={setMaximizedSlot}
          cameraFps={cameraFps}
          autoInference={autoInference}
          availableCameras={availableCameras}
          loadingCameras={loadingCameras}
          globalBusy={globalBusy}
          slotBusy={slotBusy}
          onConnectCamera={onConnectCamera}
          onDisconnectCamera={onDisconnectCamera}
          BACKEND_URL={BACKEND_URL}
        />
        <ControlBar
          streaming={streaming}
          autoInference={autoInference}
          globalBusy={globalBusy}
          slotBusy={slotBusy}
          loadingCameras={loadingCameras}
          onToggleStream={onToggleStream}
          onToggleAutoInference={onToggleAutoInference}
          onTriggerDetection={onTriggerDetection}
          onRefreshCameras={onRefreshCameras}
          onUploadImage={onViewImage}
          BACKEND_URL={BACKEND_URL}
          addLog={addLog}
        />
      </div>

      {/* Right Column: Stats Panel + Recent Alerts AlertFeed */}
      {maximizedSlot === null && (
        <div className="w-full xl:w-80 flex flex-col gap-3 shrink-0 h-full min-h-0">
          <StatsPanel
            stats={stats}
            slotMapping={slotMapping}
            cameraFps={cameraFps}
          />
          <AlertFeed
            logs={logs}
            onViewImage={onViewImage}
          />
        </div>
      )}
    </div>
  );
}
