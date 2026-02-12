// ============================================================
// DiagnosticCard Component - Modern FDD diagnosis display
// ============================================================

import { AlertTriangle, CheckCircle2, XCircle, Wrench, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter } from '../ui';
import { Badge } from '../ui';
import { ProgressBar } from '../ui';
import { Button } from '../ui';
import { cn } from '../../utils/cn';
import type { DiagnosisData as DiagnosisDataType } from '../../types';
import './DiagnosticCard.css';

interface DiagnosticCardProps {
  diagnosis: DiagnosisDataType;
  alarmId?: string;
  onDismiss?: () => void;
  onCreateTicket?: (diagnosis: DiagnosisDataType) => void;
  onExecute?: (action: string) => void;
}

const SEVERITY_CONFIG: Record<string, { label: string; variant: 'danger' | 'warning' | 'info' | 'success'; icon: any }> = {
  critical: { label: '紧急', variant: 'danger', icon: AlertTriangle },
  high: { label: '高', variant: 'danger', icon: XCircle },
  medium: { label: '中', variant: 'warning', icon: AlertCircle },
  low: { label: '低', variant: 'info', icon: CheckCircle2 },
  info: { label: '信息', variant: 'info', icon: CheckCircle2 },
};

export function DiagnosticCard({
  diagnosis,
  alarmId,
  onDismiss,
  onCreateTicket,
  onExecute,
}: DiagnosticCardProps) {
  const severityConfig = SEVERITY_CONFIG[diagnosis.severity] || SEVERITY_CONFIG.info;
  const SeverityIcon = severityConfig.icon;

  return (
    <Card variant="glass" className="diagnostic-card" data-severity={diagnosis.severity}>
      <CardHeader className="diagnostic-header">
        <div className="diagnostic-meta">
          <Badge variant={severityConfig.variant} dot>
            <SeverityIcon size={14} />
            {severityConfig.label}
          </Badge>
          <span className="diagnostic-category">{diagnosis.fault_category}</span>
          {alarmId && <span className="alarm-id">#{alarmId}</span>}
        </div>
        {onDismiss && (
          <button
            className="dismiss-btn"
            onClick={onDismiss}
            aria-label="关闭"
          >
            ×
          </button>
        )}
      </CardHeader>

      <CardContent className="diagnostic-content">
        {/* Confidence Bar */}
        <div className="confidence-section">
          <div className="confidence-label">
            <span>AI 置信度</span>
            <span className="confidence-value">{Math.round(diagnosis.confidence * 100)}%</span>
          </div>
          <ProgressBar
            value={diagnosis.confidence * 100}
            variant={diagnosis.confidence >= 0.7 ? 'success' : diagnosis.confidence >= 0.5 ? 'warning' : 'danger'}
          />
        </div>

        {/* Root Cause */}
        <div className="diagnostic-section">
          <h4 className="section-title">
            <AlertTriangle size={16} />
            根因分析
          </h4>
          <p className="root-cause">{diagnosis.root_cause}</p>
        </div>

        {/* Explanation */}
        {diagnosis.explanation && (
          <div className="diagnostic-section">
            <h4 className="section-title">
              <AlertCircle size={16} />
              分析说明
            </h4>
            <p className="explanation">{diagnosis.explanation}</p>
          </div>
        )}

        {/* RCA Chain */}
        {diagnosis.rca_chain && diagnosis.rca_chain.length > 0 && (
          <div className="diagnostic-section">
            <h4 className="section-title">
              <Wrench size={16} />
              诊断链路
            </h4>
            <div className="rca-chain">
              {diagnosis.rca_chain.map((step, index) => (
                <div
                  key={`${step.point_id}-${index}`}
                  className={cn('rca-step', step.is_abnormal && 'rca-abnormal')}
                >
                  <div className="rca-step-number">{index + 1}</div>
                  <div className="rca-step-content">
                    <span className="rca-point-name">{step.point_name}</span>
                    <span className="rca-observation">{step.observation}</span>
                  </div>
                  {step.is_abnormal && (
                    <Badge variant="danger" size="sm">异常</Badge>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Affected Equipment */}
        {diagnosis.affected_equipment && diagnosis.affected_equipment.length > 0 && (
          <div className="diagnostic-section">
            <h4 className="section-title">受影响设备</h4>
            <div className="equipment-tags">
              {diagnosis.affected_equipment.map((eq, index) => (
                <Badge key={index} variant="default">
                  {eq}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {diagnosis.recommendations && diagnosis.recommendations.length > 0 && (
          <div className="diagnostic-section">
            <h4 className="section-title">建议操作</h4>
            <div className="recommendations">
              {diagnosis.recommendations.map((rec, index) => (
                <div key={index} className="recommendation-item">
                  <div className="recommendation-number">{index + 1}</div>
                  <span className="recommendation-text">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="diagnostic-footer">
        {onExecute && (
          <Button
            variant="success"
            onClick={() => onExecute(diagnosis.recommendations?.[0] || '执行建议操作')}
          >
            <Wrench size={16} />
            执行建议
          </Button>
        )}
        {onCreateTicket && diagnosis.confidence >= 0.5 && (
          <Button
            variant="primary"
            onClick={() => onCreateTicket(diagnosis)}
          >
            创建工单
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
