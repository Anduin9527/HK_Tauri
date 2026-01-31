import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Camera, AlertCircle, Maximize2 } from 'lucide-react';

const VideoFeed = ({ streamUrl, isConnected }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(false);
    const [fullScreen, setFullScreen] = useState(false);

    useEffect(() => {
        setIsLoading(true);
        setError(false);
    }, [streamUrl]);

    return (
        <div className={clsx(
            "relative rounded-xl overflow-hidden bg-black/40 border border-white/10 shadow-2xl transition-all duration-500 group",
            fullScreen ? "fixed inset-0 z-50 rounded-none" : "w-full aspect-video"
        )}>
            {/* Header / Overlay Controls */}
            <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-b from-black/60 to-transparent">
                <div className="flex items-center gap-2">
                    <div className={clsx("w-2 h-2 rounded-full animate-pulse", isConnected ? "bg-green-500" : "bg-red-500")} />
                    <span className="text-xs font-medium text-white/80 tracking-wider">
                        {isConnected ? "实时监控" : "离线"}
                    </span>
                </div>
                <button
                    onClick={() => setFullScreen(!fullScreen)}
                    className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors backdrop-blur-md"
                >
                    <Maximize2 size={16} />
                </button>
            </div>

            {/* Video Content */}
            <div className="w-full h-full flex items-center justify-center relative">
                {!isConnected ? (
                    <div className="flex flex-col items-center gap-3 text-white/30">
                        <Camera size={48} />
                        <span className="text-sm">无摄像头信号</span>
                    </div>
                ) : (
                    <img
                        src={streamUrl}
                        alt="Live Stream"
                        className="w-full h-full object-contain"
                        onLoad={() => setIsLoading(false)}
                        onError={() => setError(true)}
                        style={{ display: isLoading || error ? 'none' : 'block' }}
                    />
                )}

                {isLoading && isConnected && !error && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
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
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="flex justify-between text-xs text-white/60 font-mono">
                    <span>RTSP: 192.168.1.64</span>
                    <span>1920x1080 @ 30fps</span>
                </div>
            </div>
        </div>
    );
};

export default VideoFeed;
