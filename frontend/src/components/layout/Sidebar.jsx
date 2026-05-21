import React from 'react';
import { Activity, AlertTriangle, Settings, Luggage, Cpu } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { id: 'dashboard', icon: Activity, label: '实时监控' },
  { id: 'logs', icon: AlertTriangle, label: '缺陷日志' },
  { id: 'settings', icon: Settings, label: '系统设置' },
];

export default function Sidebar({ activeTab, onTabChange }) {
  return (
    <aside className="glass flex w-60 shrink-0 flex-col border-r border-[var(--border)] h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[var(--border)] bg-black/10">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-blue-600 text-white">
          <Luggage size={18} />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold tracking-wider text-[var(--text-main)]">
            NEXUS-AI
          </span>
          <span className="text-[9px] font-mono tracking-widest text-[var(--text-muted)] uppercase">
            缺陷检测系统
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="mt-4 flex flex-1 flex-col gap-0.5">
        {navItems.map(({ id, icon: Icon, label }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={clsx(
                'flex items-center gap-3 px-5 py-3 text-xs font-semibold transition-all duration-150 relative cursor-pointer',
                isActive
                  ? 'bg-blue-600/10 text-blue-400 border-l-2 border-blue-500'
                  : 'text-[var(--text-muted)] hover:bg-white/[0.02] hover:text-[var(--text-main)]'
              )}
            >
              <Icon
                size={16}
                className={clsx(
                  'shrink-0',
                  isActive ? 'text-blue-400' : 'text-gray-500'
                )}
              />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="mx-4 mb-4 rounded border border-[var(--border)] bg-black/20 p-3">
        <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)] font-semibold uppercase tracking-wider">
          <div className="flex items-center gap-1.5">
            <Cpu size={12} className="text-blue-500" />
            <span>主机状态</span>
          </div>
          <span className="text-emerald-400 font-mono">OK</span>
        </div>
        <div className="mt-2.5 h-1 w-full rounded bg-white/[0.05] overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-500"
            style={{ width: '45%' }}
          />
        </div>
        <div className="mt-2 flex justify-between text-[9px] text-[var(--text-muted)] font-mono">
          <span>CPU: 45%</span>
          <span>TEMP: 42°C</span>
        </div>
      </div>
    </aside>
  );
}
