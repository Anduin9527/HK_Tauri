import React from 'react';
import { AlertTriangle, Image as ImageIcon, Bell } from 'lucide-react';
import clsx from 'clsx';

export default function AlertFeed({ logs, onViewImage }) {
  return (
    <div className="glass-card flex-1 rounded p-0 overflow-hidden flex flex-col min-h-0">
      {/* Header */}
      <div className="p-3 border-b border-[var(--border)] bg-black/10 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Bell size={14} className="text-blue-500" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-main)]">告警历史队列</h3>
        </div>
        {logs.length > 0 && (
          <span className="px-2 py-0.5 rounded text-[9px] font-bold font-mono bg-blue-600/10 text-blue-400 border border-blue-500/20">
            {logs.length}
          </span>
        )}
      </div>

      {/* Scrollable Alerts List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)] gap-2">
            <Bell size={24} className="opacity-10" />
            <span className="text-xs font-mono">STANDBY / 无历史告警</span>
          </div>
        ) : (
          logs.map((log) => {
            const isHigh = log.severity === 'high';
            const isMedium = log.severity === 'medium';
            const severityClass = isHigh
              ? 'severity-high'
              : isMedium
              ? 'severity-medium'
              : 'severity-info';

            return (
              <div
                key={log.id}
                className={clsx(
                  "flex gap-2.5 items-start p-2.5 rounded border border-[var(--border)] bg-[var(--bg-card)]",
                  severityClass
                )}
              >
                {/* Alert Icon */}
                <div className="mt-0.5 shrink-0">
                  <AlertTriangle
                    size={14}
                    className={clsx(
                      isHigh ? 'text-[var(--alarm)]' : isMedium ? 'text-[var(--warning)]' : 'text-blue-400'
                    )}
                  />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline mb-1">
                    <h4 className="text-xs font-bold text-[var(--text-main)] truncate">
                      {log.title}
                    </h4>
                    <span className="text-[9px] text-[var(--text-muted)] font-mono">
                      {log.time}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                      {log.message}
                    </p>
                    {log.attachment && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewImage(log.attachment);
                        }}
                        className="p-1 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/20 rounded text-blue-400 transition-colors shrink-0 cursor-pointer"
                        title="查看缺陷图片"
                      >
                        <ImageIcon size={12} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
