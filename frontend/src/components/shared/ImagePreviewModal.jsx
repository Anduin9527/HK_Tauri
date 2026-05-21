import React from 'react';
import { X } from 'lucide-react';

export default function ImagePreviewModal({ imageUrl, onClose }) {
  if (!imageUrl) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={onClose}
    >
      {/* Inner Container */}
      <div
        className="relative mx-4 flex max-w-[90vw] flex-col items-center rounded border border-[var(--border)] bg-[var(--bg-card)] p-3"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded border border-[var(--border)] bg-[var(--bg-card)] text-white/70 hover:text-white transition-colors cursor-pointer"
        >
          <X size={12} />
        </button>

        {/* Image */}
        <img
          src={imageUrl}
          alt="检测结果预览"
          className="max-h-[85vh] max-w-full rounded object-contain border border-black/40"
        />

        {/* Footer */}
        <p className="mt-2.5 text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
          点击背景关闭 · IMAGE_PREVIEW_ANALYSIS
        </p>
      </div>
    </div>
  );
}
