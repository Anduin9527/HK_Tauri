import React from 'react';
import { Cpu } from 'lucide-react';
import clsx from 'clsx';

export default function ModelSelector({
  modelName,
  modelType,
  availableModels,
  loading,
  onApplyModelSelection,
}) {
  return (
    <div className="space-y-3 bg-[var(--bg-card)] p-3.5 rounded border border-[var(--border)]">
      <div className="flex items-center gap-1.5 text-blue-500">
        <Cpu size={14} />
        <h4 className="text-xs font-bold text-[var(--text-main)]">推理模型 (Model)</h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Model Series Selector */}
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
            模型系列
          </label>
          <select
            value={modelName}
            onChange={(e) => onApplyModelSelection(e.target.value, modelType)}
            disabled={loading}
            className="w-full bg-black/20 border border-[var(--border)] rounded px-2.5 py-1.5 text-xs text-[var(--text-main)] focus:border-blue-500 outline-none transition-all cursor-pointer"
          >
            {(availableModels.length ? availableModels.map(m => m.name) : ['yolo26s']).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>

        {/* Inference Engine Backend Selector */}
        <div className="space-y-1">
          <label className="text-[9px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
            推理后端
          </label>
          <select
            value={modelType}
            onChange={(e) => onApplyModelSelection(modelName, e.target.value)}
            disabled={loading}
            className="w-full bg-black/20 border border-[var(--border)] rounded px-2.5 py-1.5 text-xs text-[var(--text-main)] focus:border-blue-500 outline-none transition-all cursor-pointer"
          >
            <option value="auto">auto (优先 OpenVINO)</option>
            <option value="openvino">openvino (硬件加速)</option>
            <option value="onnx">onnx (标准后端)</option>
            <option value="pt">pt (PyTorch 原生)</option>
          </select>
        </div>
      </div>

      <p className="text-[9px] text-[var(--text-muted)] leading-relaxed italic">
        * 提示：系统会自动寻找模型目录下最佳匹配的模型权重。文件名中含有 best.* 的文件将被默认重命名并加载为 yolo26s 的兼容权重。
      </p>
    </div>
  );
}
