import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Camera, AlertCircle, Maximize2, Minimize2, Eye, EyeOff } from 'lucide-react';

const VideoFeed = ({ streamUrl, isConnected, onMaximize, isMaximized, fps, autoInference }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(false);
    const [showDetections, setShowDetections] = useState(true);
    const [activeUrl, setActiveUrl] = useState("");
    const [lastGoodUrl, setLastGoodUrl] = useState("");
    const retryRef = React.useRef({ attempt: 0, timer: null });

    const profile = 'grid';
    const finalUrl = streamUrl ? `${streamUrl}?type=${showDetections ? 'detect' : 'raw'}&profile=${profile}` : "";

    useEffect(() => {
        // Clear any pending retry on URL/toggle change
        if (retryRef.current.timer) {
            clearTimeout(retryRef.current.timer);
            retryRef.current.timer = null;
        }
        retryRef.current.attempt = 0;

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
    }, [streamUrl, showDetections, profile]);

    // Cleanup retry timer on unmount
    useEffect(() => {
        return () => {
            if (retryRef.current.timer) clearTimeout(retryRef.current.timer);
        };
    }, []);

    return (
        <div className="relative rounded bg-[var(--bg-card)] border border-[var(--border)] transition-all duration-300 group w-full h-full">
            {isConnected && fps && (
                <div className="absolute top-8 left-2 z-20 px-2 py-0.5 bg-black/80 rounded border border-white/10 text-[9px] font-bold font-mono text-[var(--text-main)]">
                    {showDetections && autoInference ? (
                        <div className="flex flex-col gap-0.5">
                            <div>FPS: {Number(fps.camera_fps ?? fps.capture_fps ?? fps.stream_fps ?? 0).toFixed(1)}</div>
                            <div>INF: {Number(fps.infer_ms ?? 0).toFixed(1)}ms</div>
                        </div>
                    ) : (
                        <div>FPS: {Number(fps.camera_fps ?? fps.capture_fps ?? fps.stream_fps ?? 0).toFixed(1)}</div>
                    )}
                </div>
            )}
            
            {/* Header / Overlay Controls */}
            <div className="absolute top-0 left-0 right-0 p-2 flex justify-between items-center z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-150 bg-black/80 border-b border-white/5">
                <div className="flex items-center gap-1.5">
                    <div className={clsx("w-1.5 h-1.5 rounded-full", isConnected ? "bg-emerald-500" : "bg-red-500")} />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/90">
                        {isConnected ? "ONLINE" : "STANDBY"}
                    </span>
                </div>
                
                <div className="flex items-center gap-1.5">
                     {/* Toggle Detections Button */}
                    {isConnected && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowDetections(prev => !prev);
                            }}
                            className={clsx(
                                "p-1.5 rounded transition-colors cursor-pointer",
                                showDetections ? "bg-blue-600 text-white" : "bg-white/10 text-white/70 hover:bg-white/20"
                            )}
                            title={showDetections ? "隐藏检测标注" : "显示检测标注"}
                        >
                            {showDetections ? <Eye size={12} /> : <EyeOff size={12} />}
                        </button>
                    )}
                    
                    <button
                        onClick={onMaximize}
                        className="p-1.5 rounded bg-white/10 hover:bg-white/20 text-white transition-colors cursor-pointer"
                        title={isMaximized ? "退出全屏" : "全屏查看"}
                    >
                        {isMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                    </button>
                </div>
            </div>

            {/* Video Content */}
            <div className="w-full h-full flex items-center justify-center relative">
                {!isConnected ? (
                    <div className="flex flex-col items-center gap-1.5 text-[var(--text-muted)] font-mono">
                        <Camera size={24} className="opacity-40" />
                        <span className="text-[10px] tracking-wider uppercase font-semibold">NO CAMERA Connected</span>
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
                                "w-full h-full object-contain",
                                error ? "opacity-0" : "opacity-100",
                                isLoading && lastGoodUrl && lastGoodUrl !== activeUrl ? "opacity-0" : "opacity-100"
                            )}
                            onLoad={() => {
                                setLastGoodUrl(activeUrl);
                                setIsLoading(false);
                                setError(false);
                                retryRef.current.attempt = 0;
                            }}
                            onError={() => {
                                setError(true);
                                setIsLoading(false);
                                // Retry with exponential backoff (1s, 2s, 4s, max 8s)
                                const attempt = retryRef.current.attempt;
                                if (attempt < 5 && isConnected && activeUrl) {
                                    const delay = Math.min(1000 * Math.pow(2, attempt), 8000);
                                    retryRef.current.attempt = attempt + 1;
                                    retryRef.current.timer = setTimeout(() => {
                                        setActiveUrl(prev => prev + (prev.includes('?') ? '&' : '?') + '_t=' + Date.now());
                                    }, delay);
                                }
                            }}
                        />
                    </>
                )}

                {isLoading && isConnected && !error && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-6 h-6 border border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                    </div>
                )}

                {error && isConnected && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400 gap-1 bg-black/80 font-mono">
                        <AlertCircle size={20} />
                        <span className="text-[10px] uppercase font-bold tracking-wider">MEDIA_STREAM_ERROR</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VideoFeed;
