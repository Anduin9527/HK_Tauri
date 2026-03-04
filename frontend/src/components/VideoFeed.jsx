import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Camera, AlertCircle, Maximize2, Minimize2, Eye, EyeOff } from 'lucide-react';

const VideoFeed = ({ streamUrl, isConnected, onMaximize, isMaximized, fps, autoInference }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(false);
    // const [fullScreen, setFullScreen] = useState(false); // Removed internal fullscreen state
    const [showDetections, setShowDetections] = useState(true);
    const [activeUrl, setActiveUrl] = useState("");
    const [lastGoodUrl, setLastGoodUrl] = useState("");

    // Use consistent profile to prevent reloading on maximize/minimize
    const profile = 'grid'; // Always use grid profile for seamless transition
    const finalUrl = streamUrl ? `${streamUrl}?type=${showDetections ? 'detect' : 'raw'}&profile=${profile}` : "";

    useEffect(() => {
        if (!finalUrl) {
            setActiveUrl("");
            setLastGoodUrl("");
            setIsLoading(false);
            setError(false);
            return;
        }
        setActiveUrl(finalUrl);
        setIsLoading(true);
        setError(false);
    }, [streamUrl, showDetections, profile]); // Reload when URL or toggle changes

    return (
        <div className={clsx(
            "relative rounded-xl overflow-hidden bg-[var(--bg-card)] border border-[var(--border)] shadow-2xl transition-all duration-500 group w-full h-full",
            // fullScreen ? "fixed inset-0 z-50 rounded-none" : "w-full aspect-video" // Controlled by parent grid now
        )}>
            {isConnected && fps && (
                <div className="absolute top-10 left-2 z-20 px-2 py-1 bg-black/60 rounded text-xs font-mono text-white/80 backdrop-blur-md">
                    {showDetections && autoInference ? (
                        <>
                            <div>Cam {Number(fps.camera_fps ?? fps.capture_fps ?? fps.stream_fps ?? 0).toFixed(1)} FPS</div>
                            <div className="text-[10px] text-white/70">
                                Infer {Number(fps.infer_fps ?? 0).toFixed(1)} | {Number(fps.infer_ms ?? 0).toFixed(1)}ms
                            </div>
                        </>
                    ) : (
                        <div>Cam {Number(fps.camera_fps ?? fps.capture_fps ?? fps.stream_fps ?? 0).toFixed(1)} FPS</div>
                    )}
                </div>
            )}
            {/* Header / Overlay Controls */}
            <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-b from-black/60 to-transparent">
                <div className="flex items-center gap-2">
                    <div className={clsx("w-2 h-2 rounded-full animate-pulse", isConnected ? "bg-green-500" : "bg-red-500")} />
                    <span className="text-xs font-medium text-white/90 tracking-wider">
                        {isConnected ? "实时监控" : "离线"}
                    </span>
                </div>
                
                <div className="flex items-center gap-2">
                     {/* Toggle Detections Button */}
                    {isConnected && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowDetections(prev => !prev);
                            }}
                            className={clsx(
                                "p-2 rounded-lg transition-colors backdrop-blur-md",
                                showDetections ? "bg-indigo-500/80 text-white hover:bg-indigo-500" : "bg-black/30 text-white/70 hover:bg-black/50"
                            )}
                            title={showDetections ? "隐藏检测结果" : "显示检测结果"}
                        >
                            {showDetections ? <Eye size={16} /> : <EyeOff size={16} />}
                        </button>
                    )}
                    
                    <button
                        onClick={onMaximize}
                        className="p-2 rounded-lg bg-black/30 hover:bg-black/50 text-white transition-colors backdrop-blur-md"
                        title={isMaximized ? "退出全屏" : "全屏查看"}
                    >
                        {isMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>
                </div>
            </div>

            {/* Video Content */}
            <div className="w-full h-full flex items-center justify-center relative">
                {!isConnected ? (
                    <div className="flex flex-col items-center gap-3 text-[var(--text-muted)]">
                        <Camera size={48} />
                        <span className="text-sm">无摄像头信号</span>
                    </div>
                ) : (
                    <>
                        {lastGoodUrl && (isLoading || error) && lastGoodUrl !== activeUrl && (
                            <img
                                src={lastGoodUrl}
                                alt="Last Frame"
                                className="absolute inset-0 w-full h-full object-contain"
                            />
                        )}
                        <img
                            src={activeUrl}
                            alt="Live Stream"
                            className={clsx(
                                "w-full h-full object-contain transition-opacity duration-200",
                                error ? "opacity-0" : "opacity-100",
                                isLoading && lastGoodUrl && lastGoodUrl !== activeUrl ? "opacity-0" : "opacity-100"
                            )}
                            onLoad={() => {
                                setLastGoodUrl(activeUrl);
                                setIsLoading(false);
                                setError(false);
                            }}
                            onError={() => {
                                setError(true);
                                setIsLoading(false);
                            }}
                        />
                    </>
                )}

                {isLoading && isConnected && !error && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                    </div>
                )}

                {error && isConnected && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400 gap-2 bg-black/50">
                        <AlertCircle size={32} />
                        <span className="text-sm">流媒体错误</span>
                    </div>
                )}
            </div>

            {/* ROI / Stats Overlay (Placeholder) */}
            {/* <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="flex justify-between text-xs text-white/60 font-mono">
                    <span>RTSP: 192.168.1.64</span>
                    <span>1920x1080 @ 30fps</span>
                </div>
            </div> */}
        </div>
    );
};

export default VideoFeed;
