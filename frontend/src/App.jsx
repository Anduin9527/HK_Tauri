import React, { useState } from 'react';
import './App.css';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import DashboardView from './components/dashboard/DashboardView';
import LogsView from './components/logs/LogsView';
import SettingsView from './components/settings/SettingsView';
import ImagePreviewModal from './components/shared/ImagePreviewModal';
import { useBackendConnection } from './hooks/useBackendConnection';
import { useCameraManager } from './hooks/useCameraManager';
import { useSettings } from './hooks/useSettings';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [debugImage, setDebugImage] = useState(null);

  const connection = useBackendConnection();
  const cameraManager = useCameraManager(connection.addLog);
  const settings = useSettings(connection.addLog);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-dark)] app-root">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header Bar */}
        <Header activeTab={activeTab} />

        {/* Dynamic Tab Views */}
        <main className="flex-1 overflow-hidden p-5 min-h-0 relative z-10">
          {activeTab === 'dashboard' && (
            <DashboardView
              streaming={cameraManager.streaming}
              slotMapping={cameraManager.slotMapping}
              maximizedSlot={cameraManager.maximizedSlot}
              setMaximizedSlot={cameraManager.setMaximizedSlot}
              cameraFps={connection.cameraFps}
              autoInference={connection.autoInference}
              stats={connection.stats}
              logs={connection.logs}
              availableCameras={cameraManager.availableCameras}
              loadingCameras={cameraManager.loadingCameras}
              globalBusy={cameraManager.globalBusy}
              slotBusy={cameraManager.slotBusy}
              onConnectCamera={cameraManager.connectCamera}
              onDisconnectCamera={cameraManager.disconnectCamera}
              onToggleStream={cameraManager.toggleStream}
              onToggleAutoInference={connection.toggleAutoInference}
              onTriggerDetection={connection.triggerDetection}
              onRefreshCameras={cameraManager.refreshCameras}
              onViewImage={setDebugImage}
              addLog={connection.addLog}
              BACKEND_URL={connection.BACKEND_URL}
            />
          )}

          {activeTab === 'logs' && (
            <LogsView
              logs={connection.logs}
              onRefreshLogs={connection.refreshLogs}
              onViewImage={setDebugImage}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView settings={settings} />
          )}
        </main>
      </div>

      {/* Image Preview Overlay Modal */}
      <ImagePreviewModal
        imageUrl={debugImage}
        onClose={() => setDebugImage(null)}
      />
    </div>
  );
}

export default App;
