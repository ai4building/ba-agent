// ============================================================
// HMI Preview Component
// Auto-generated HMI layout preview with confirmation
// ============================================================

import { Monitor, Check, Download, Eye } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useState } from 'react';

export interface HmiWidget {
  type: 'gauge' | 'chart' | 'status' | 'toggle' | 'setpoint';
  id: string;
  label: string;
  dataBinding: string;
  position: { row: number; col: number };
}

export interface HmiPage {
  name: string;
  layout: 'grid' | 'flex';
  widgets: HmiWidget[];
}

export interface HmiLayout {
  equip_id: string;
  equip_name: string;
  confidence: number;
  pages: HmiPage[];
  matched_components: number;
  total_components: number;
}

interface HmiPreviewProps {
  layout: HmiLayout;
  onConfirm?: () => void;
  onExport?: () => void;
  className?: string;
}

export function HmiPreview({ layout, onConfirm, onExport, className }: HmiPreviewProps) {
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  const [previewMode, setPreviewMode] = useState<'preview' | 'code'>('preview');
  const selectedPage = layout.pages[selectedPageIndex];

  return (
    <div className={cn('rounded-xl border border-slate-200 bg-white overflow-hidden', className)}>
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="w-5 h-5 text-indigo-600" />
            <span className="font-semibold text-slate-900">HMI 自动生成</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">
              匹配度 {layout.confidence}%
            </span>
            <span className="text-xs text-slate-400">·</span>
            <span className="text-xs text-slate-500">
              {layout.matched_components}/{layout.total_components} 组件
            </span>
          </div>
        </div>
        <div className="mt-2 text-sm text-slate-600">
          {layout.equip_name} · <span className="font-mono text-xs">{layout.equip_id}</span>
        </div>
      </div>

      {/* Page Tabs */}
      {layout.pages.length > 1 && (
        <div className="flex border-b border-slate-200 bg-slate-50">
          {layout.pages.map((page, index) => (
            <button
              key={index}
              onClick={() => setSelectedPageIndex(index)}
              className={cn(
                'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                index === selectedPageIndex
                  ? 'border-indigo-500 text-indigo-700 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              )}
            >
              {page.name}
            </button>
          ))}
        </div>
      )}

      {/* Preview Area */}
      <div className="p-4">
        {previewMode === 'preview' ? (
          <div className="bg-slate-100 rounded-lg p-4 min-h-[200px]">
            {/* Simulated HMI Preview */}
            <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
              <div className="text-sm font-medium text-slate-700 mb-3">{selectedPage.name}</div>
              <div className={cn(
                'grid gap-3',
                selectedPage.layout === 'grid' ? 'grid-cols-3' : 'flex flex-col'
              )}>
                {selectedPage.widgets.map((widget, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg border border-slate-200"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-slate-600">{widget.label}</span>
                      <span className={cn(
                        'w-2 h-2 rounded-full',
                        widget.type === 'status' ? 'bg-green-400' : 'bg-slate-300'
                      )} />
                    </div>
                    <div className="text-xs text-slate-400 font-mono truncate">
                      {widget.dataBinding}
                    </div>
                    <div className="mt-2 flex items-center justify-center h-12 bg-white rounded border border-slate-200">
                      <span className="text-lg text-slate-300">
                        {widget.type === 'gauge' ? '🎯' :
                         widget.type === 'chart' ? '📈' :
                         widget.type === 'status' ? '●' :
                         widget.type === 'toggle' ? '🔘' : '⚙️'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
            <pre className="text-xs text-green-400 font-mono">
              {JSON.stringify(selectedPage, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPreviewMode(previewMode === 'preview' ? 'code' : 'preview')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5',
              previewMode === 'preview'
                ? 'bg-white text-slate-700 border border-slate-200'
                : 'bg-indigo-100 text-indigo-700'
            )}
          >
            <Eye className="w-4 h-4" />
            预览
          </button>
          <button
            onClick={() => setPreviewMode(previewMode === 'code' ? 'code' : 'code')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5',
              previewMode === 'code'
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-white text-slate-700 border border-slate-200'
            )}
          >
            <span className="font-mono">&lt;/&gt;</span>
            代码
          </button>
        </div>

        <div className="flex items-center gap-2">
          {onExport && (
            <button
              onClick={onExport}
              className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              导出
            </button>
          )}
          {onConfirm && (
            <button
              onClick={onConfirm}
              className="px-4 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-indigo-500/30 flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              确认发布到 FIN
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
