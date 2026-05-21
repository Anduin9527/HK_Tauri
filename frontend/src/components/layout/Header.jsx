import React from 'react';
import clsx from 'clsx';

const pageTitles = {
  dashboard: '实时推理监控',
  logs: '缺陷日志历史',
  settings: '系统设置',
};

export default function Header({ activeTab }) {
  const title = pageTitles[activeTab] ?? '实时推理监控';

  return (
    <header className="glass flex h-12 shrink-0 items-center justify-between border-b border-[var(--border)] px-5 bg-black/10">
      {/* Page Title */}
      <h1 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">
        <span className="text-[var(--text-muted)] font-normal">旅行箱检测系统 · </span>
        {title}
      </h1>

      {/* Status Badge */}
      <div className="flex items-center gap-2 rounded border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5">
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
        </span>
        <span className="text-[10px] font-bold font-mono text-emerald-400 uppercase tracking-wider">SYS_READY</span>
      </div>
    </header>
  );
}
