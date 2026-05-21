import React, { useState, useMemo } from 'react';
import { Search, RefreshCw, Image as ImageIcon, Info } from 'lucide-react';
import clsx from 'clsx';

export default function LogsView({ logs, onRefreshLogs, onViewImage }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all"); // 'all', 'high', 'medium', 'info'

  // Local filter logic
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // Search text match (title or message)
      const matchesSearch =
        (log.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        (log.message || "").toLowerCase().includes(searchQuery.toLowerCase());

      // Severity level match
      let matchesSeverity = true;
      if (severityFilter === "high") {
        matchesSeverity = log.severity === "high";
      } else if (severityFilter === "medium") {
        matchesSeverity = log.severity === "medium";
      } else if (severityFilter === "info") {
        // match info, low, default info
        matchesSeverity = log.severity !== "high" && log.severity !== "medium";
      }

      return matchesSearch && matchesSeverity;
    });
  }, [logs, searchQuery, severityFilter]);

  return (
    <div className="flex flex-col h-full gap-3 min-h-0 page-enter">
      {/* Top Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between bg-[var(--bg-card)] border border-[var(--border)] p-3 rounded shrink-0">
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search Input */}
          <div className="relative flex-1 md:flex-none md:w-64">
            <input
              type="text"
              placeholder="搜索日志标题或详情..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/20 border border-[var(--border)] rounded pl-8 pr-3 py-1 text-xs text-[var(--text-main)] outline-none focus:border-blue-500 transition-colors"
            />
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          </div>

          {/* Severity Filters */}
          <div className="flex items-center bg-black/20 p-0.5 rounded border border-[var(--border)]">
            {[
              { id: 'all', label: '全部' },
              { id: 'high', label: '重要告警' },
              { id: 'medium', label: '一般告警' },
              { id: 'info', label: '系统通知' },
            ].map((pill) => (
              <button
                key={pill.id}
                onClick={() => setSeverityFilter(pill.id)}
                className={clsx(
                  "px-2.5 py-1 rounded-sm text-[10px] font-semibold transition-all cursor-pointer",
                  severityFilter === pill.id
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white"
                )}
              >
                {pill.label}
              </button>
            ))}
          </div>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefreshLogs}
          className="w-full md:w-auto flex items-center justify-center gap-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs font-semibold text-white transition-all shrink-0 cursor-pointer"
        >
          <RefreshCw size={12} />
          <span>刷新日志</span>
        </button>
      </div>

      {/* Logs Table Container */}
      <div className="flex-1 overflow-auto border border-[var(--border)] bg-[var(--bg-card)] rounded min-h-0">
        <table className="w-full text-left border-collapse">
          <thead className="bg-black/20 text-gray-400 text-xs sticky top-0 border-b border-[var(--border)] z-10">
            <tr>
              <th className="p-3 font-bold w-28 text-[10px] uppercase tracking-wider">时间</th>
              <th className="p-3 font-bold w-20 text-[10px] uppercase tracking-wider">级别</th>
              <th className="p-3 font-bold w-32 text-[10px] uppercase tracking-wider">模块</th>
              <th className="p-3 font-bold text-[10px] uppercase tracking-wider">日志详情</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)] text-xs">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-20 text-center text-gray-500">
                  <div className="flex flex-col items-center gap-1.5">
                    <Info size={20} className="opacity-20 text-blue-500" />
                    <span className="font-mono text-xs">NO RECORD / 没有找到日志记录</span>
                  </div>
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr
                  key={log.id || `${log.time}-${log.title}-${log.message}`}
                  className="hover:bg-white/[0.02] transition-colors group/row"
                >
                  {/* Time */}
                  <td className="p-3 font-mono text-[var(--text-muted)] whitespace-nowrap text-[11px]">
                    {log.time}
                  </td>

                  {/* Severity Badge */}
                  <td className="p-3">
                    <span
                      className={clsx(
                        "px-2 py-0.5 rounded text-[9px] font-bold uppercase border tracking-wider",
                        log.severity === 'high'
                          ? "bg-red-500/10 text-red-400 border-red-500/20"
                          : log.severity === 'medium'
                          ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                          : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                      )}
                    >
                      {log.severity === 'high' ? 'HIGH' : log.severity === 'medium' ? 'WARN' : 'INFO'}
                    </span>
                  </td>

                  {/* Title / Module */}
                  <td className="p-3 font-bold text-[var(--text-main)] whitespace-nowrap">
                    {log.title}
                  </td>

                  {/* Message details / Attachment preview */}
                  <td className="p-3 text-gray-300">
                    <div className="flex items-center justify-between gap-4">
                      <span className="leading-relaxed text-[11px]">{log.message}</span>
                      {log.attachment && (
                        <button
                          onClick={() => onViewImage(log.attachment)}
                          className="flex items-center gap-1 px-2 py-0.5 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/20 rounded text-blue-400 transition-all text-[9px] font-bold whitespace-nowrap opacity-80 group-hover/row:opacity-100 cursor-pointer"
                        >
                          <ImageIcon size={10} />
                          <span>查看图片</span>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
