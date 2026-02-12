// ============================================================
// OptimizationPanel Component - Modern energy optimization display
// ============================================================

import { Zap, TrendingDown, CheckCircle2, XCircle, Settings, ArrowRight } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter } from '../ui';
import { Badge } from '../ui';
import { Button } from '../ui';
import { ProgressBar } from '../ui';
import { cn } from '../../utils/cn';
import type { OptimizationData as OptimizationDataType, SetpointRecommendation } from '../../types';
import './OptimizationPanel.css';

interface OptimizationPanelProps {
  optimization: OptimizationDataType;
  onApply?: (optimization: OptimizationDataType) => void;
  onDismiss?: () => void;
}

function SetpointRow({ setpoint }: { setpoint: SetpointRecommendation }) {
  const { point_name, current_value, recommended_value, unit, priority } = setpoint;
  const estimatedSavings = (setpoint as any).estimated_savings;
  const diff = recommended_value - current_value;
  const isIncrease = diff > 0;

  return (
    <div className={cn('setpoint-row', `priority-${priority}`)}>
      <div className="setpoint-info">
        <span className="setpoint-name">{point_name}</span>
        <Badge variant={priority === 'high' ? 'danger' : priority === 'medium' ? 'warning' : 'info'} size="sm">
          {priority} 优先级
        </Badge>
      </div>

      <div className="setpoint-values">
        <div className="value-current">
          <span className="value-label">当前</span>
          <span className="value-number">{current_value.toFixed(1)}</span>
          <span className="value-unit">{unit}</span>
        </div>

        <div className="value-arrow">
          <ArrowRight size={16} className={isIncrease ? 'arrow-up' : 'arrow-down'} />
        </div>

        <div className="value-recommended">
          <span className="value-label">推荐</span>
          <span className="value-number">{recommended_value.toFixed(1)}</span>
          <span className="value-unit">{unit}</span>
        </div>

        {diff !== 0 && (
          <div className={cn('value-change', isIncrease ? 'change-positive' : 'change-negative')}>
            {isIncrease ? '+' : ''}{diff.toFixed(1)}
          </div>
        )}
      </div>

      {estimatedSavings && (
        <div className="setpoint-savings">
          <TrendingDown size={12} />
          <span>省 {estimatedSavings}%</span>
        </div>
      )}
    </div>
  );
}

export function OptimizationPanel({
  optimization,
  onApply,
  onDismiss,
}: OptimizationPanelProps) {
  const {
    equip_name,
    current_energy,
    predicted_savings,
    savings_percent,
    setpoints,
    rationale,
  } = optimization;

  return (
    <Card variant="glass" className="optimization-panel">
      <CardHeader className="optimization-header">
        <div className="optimization-title-section">
          <div className="optimization-icon">
            <Zap size={24} />
          </div>
          <div className="optimization-info">
            <h3 className="optimization-title">能耗优化建议</h3>
            <p className="optimization-subtitle">{equip_name}</p>
          </div>
        </div>
        {onDismiss && (
          <button
            className="optimization-dismiss"
            onClick={onDismiss}
            aria-label="关闭"
          >
            ×
          </button>
        )}
      </CardHeader>

      <CardContent className="optimization-content">
        {/* Savings Highlight */}
        <div className="savings-highlight">
          <div className="savings-info">
            <TrendingDown size={32} className="savings-trend-icon" />
            <div className="savings-text">
              <span className="savings-value">{savings_percent.toFixed(1)}%</span>
              <span className="savings-label">预计节能</span>
            </div>
          </div>
          <div className="savings-amount">
            <span className="savings-currency">¥</span>
            <span className="savings-number">{predicted_savings.toLocaleString()}</span>
            <span className="savings-period">/年</span>
          </div>
        </div>

        {/* Current Energy */}
        <div className="current-energy-section">
          <div className="energy-label">
            <span>当前年能耗</span>
            <Settings size={14} className="energy-icon" />
          </div>
          <div className="energy-value">
            <span className="energy-number">{current_energy.toLocaleString()}</span>
            <span className="energy-unit">kWh</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="savings-progress">
          <div className="progress-labels">
            <span>优化前</span>
            <span>优化后 (预计)</span>
          </div>
          <div className="progress-bars">
            <div className="progress-bar-wrapper">
              <ProgressBar value={100} variant="default" showLabel={false} />
              <span className="progress-label-end">100%</span>
            </div>
            <div className="progress-bar-wrapper progress-reversed">
              <ProgressBar
                value={100 - savings_percent}
                variant="success"
                showLabel={false}
              />
              <span className="progress-label-end">{100 - savings_percent}%</span>
            </div>
          </div>
        </div>

        {/* Rationale */}
        {rationale && (
          <div className="rationale-section">
            <h4 className="section-title">分析说明</h4>
            <p className="rationale-text">{rationale}</p>
          </div>
        )}

        {/* Setpoint Recommendations */}
        {setpoints && setpoints.length > 0 && (
          <div className="setpoints-section">
            <h4 className="section-title">
              <Settings size={16} />
              推荐设定值调整
              <Badge variant="blue" size="sm">{setpoints.length} 项</Badge>
            </h4>
            <div className="setpoints-list">
              {setpoints.map((setpoint) => (
                <SetpointRow key={setpoint.point_id} setpoint={setpoint} />
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="optimization-footer">
        <Button variant="secondary">
          <XCircle size={16} />
          忽略建议
        </Button>
        <Button variant="success" onClick={() => onApply?.(optimization)}>
          <CheckCircle2 size={16} />
          应用优化
        </Button>
      </CardFooter>
    </Card>
  );
}
