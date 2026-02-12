// ============================================================
// Diagnostic Card Component
// FDD (Fault Detection and Diagnosis) result display
// ============================================================

import { AlertTriangle, CheckCircle2, Wrench, TrendingUp, AlertCircle } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface DiagnosticData {
  equip_id: string;
  equip_name: string;
  issue_type: string;
  severity: 'critical' | 'warning' | 'info';
  root_cause: string;
  confidence: number;
  current_values: Record<string, { value: string; status: 'normal' | 'abnormal' }>;
  recommended_actions: {
    action: string;
    auto_executable: boolean;
  }[];
  predicted_impact?: string;
}

interface DiagnosticCardProps {
  diagnosis: DiagnosticData;
  onExecuteAction?: (action: string) => void;
  onCreateTicket?: () => void;
  className?: string;
}

const severityConfig = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    icon: AlertCircle,
    label: '严重',
  },
  warning: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
    icon: AlertTriangle,
    label: '警告',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    icon: TrendingUp,
    label: '提示',
  },
};

export function DiagnosticCard({ diagnosis, onExecuteAction, onCreateTicket, className }: DiagnosticCardProps) {
  const config = severityConfig[diagnosis.severity];
  const SeverityIcon = config.icon;

  return (
    <div className={cn('rounded-xl border overflow-hidden bg-white', config.border, className)}>
      {/* Header */}
      <div className={cn('px-4 py-3 flex items-center justify-between', config.bg)}>
        <div className="flex items-center gap-2">
          <SeverityIcon className={cn('w-5 h-5', config.text)} />
          <span className={cn('font-semibold', config.text)}>{config.label}</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-600">{diagnosis.issue_type}</span>
        </div>
        <div className={cn('px-2 py-1 rounded-md bg-white/60 text-xs font-medium', config.text)}>
          置信度 {diagnosis.confidence}%
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Equipment Info */}
        <div>
          <div className="text-xs text-slate-500 mb-1">设备</div>
          <div className="font-medium text-slate-900">{diagnosis.equip_name}</div>
          <div className="text-xs text-slate-400 font-mono">{diagnosis.equip_id}</div>
        </div>

        {/* Root Cause */}
        <div className="p-3 bg-slate-50 rounded-lg">
          <div className="text-xs text-slate-500 mb-1">根因分析</div>
          <div className="text-sm text-slate-800">{diagnosis.root_cause}</div>
        </div>

        {/* Current Values */}
        <div>
          <div className="text-xs text-slate-500 mb-2">实时状态</div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(diagnosis.current_values).map(([key, data]) => (
              <div
                key={key}
                className={cn(
                  'flex items-center justify-between p-2 rounded-lg border',
                  data.status === 'abnormal' ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
                )}
              >
                <span className="text-xs text-slate-600">{key}</span>
                <div className="flex items-center gap-1">
                  <span className={cn(
                    'text-sm font-medium',
                    data.status === 'abnormal' ? 'text-red-700' : 'text-green-700'
                  )}>
                    {data.value}
                  </span>
                  {data.status === 'abnormal' && (
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                  )}
                  {data.status === 'normal' && (
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recommended Actions */}
        <div>
          <div className="text-xs text-slate-500 mb-2">建议操作</div>
          <div className="space-y-2">
            {diagnosis.recommended_actions.map((action, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg group hover:bg-slate-100 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
                  <span className="text-sm text-slate-700">{action.action}</span>
                </div>
                {action.auto_executable && onExecuteAction ? (
                  <button
                    onClick={() => onExecuteAction(action.action)}
                    className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium rounded-lg transition-colors"
                  >
                    执行 AXON
                  </button>
                ) : (
                  <span className="text-xs text-slate-400">需人工确认</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Predicted Impact */}
        {diagnosis.predicted_impact && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="text-xs text-blue-600 mb-1">预测影响</div>
            <div className="text-sm text-blue-800">{diagnosis.predicted_impact}</div>
          </div>
        )}

        {/* Footer Actions */}
        {onCreateTicket && (
          <div className="flex items-center justify-between pt-2 border-t border-slate-200">
            <button
              onClick={onCreateTicket}
              className="text-sm text-slate-600 hover:text-blue-600 transition-colors"
            >
              创建工单
            </button>
            <span className="text-xs text-slate-400">
              由 AI Agent 自动诊断 · 双脑协同处理
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
