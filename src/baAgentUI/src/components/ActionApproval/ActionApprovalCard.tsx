// ============================================================
// ActionApprovalCard — Single AI action approval card
// ============================================================

import { useState } from 'react';
import type { PendingAiAction } from '../../types';

interface ActionApprovalCardProps {
  action: PendingAiAction;
  onApprove: (actionId: string) => void;
  onReject: (actionId: string) => void;
  onStartReview: (actionId: string) => void;
}

export function ActionApprovalCard({
  action,
  onApprove,
  onReject,
  onStartReview,
}: ActionApprovalCardProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const delta = action.suggestedValue - action.currentValue;
  const deltaSign = delta >= 0 ? '+' : '';
  const confidencePercent = Math.round(action.confidence * 100);

  const timeLeft = action.expiresAt
    ? Math.max(0, Math.round((action.expiresAt.getTime() - Date.now()) / 60000))
    : null;

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      onApprove(action.id);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    setIsProcessing(true);
    try {
      onReject(action.id);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div
      className={`approval-card ${action.isLifeSafety ? 'approval-card--safety' : ''} ${
        action.status === 'reviewing' ? 'approval-card--reviewing' : ''
      }`}
      onClick={() => action.status === 'pending' && onStartReview(action.id)}
    >
      {/* Header */}
      <div className="approval-card__header">
        <div className="approval-card__point">
          {action.isLifeSafety && <span className="approval-card__lock-icon">&#128274;</span>}
          <span className="approval-card__point-name">{action.pointName}</span>
        </div>
        <span className="approval-card__equip">{action.equipName}</span>
      </div>

      {/* Values */}
      <div className="approval-card__values">
        <div className="approval-card__current">
          <span className="approval-card__label">Current</span>
          <span className="approval-card__val">
            {action.currentValue} {action.unit}
          </span>
        </div>
        <div className="approval-card__arrow">&#8594;</div>
        <div className="approval-card__suggested">
          <span className="approval-card__label">Suggested</span>
          <span className="approval-card__val">
            {action.suggestedValue} {action.unit}
          </span>
        </div>
        <div className="approval-card__delta">
          <span className="approval-card__label">Delta</span>
          <span className="approval-card__val">
            {deltaSign}{delta.toFixed(1)} {action.unit}
          </span>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="approval-card__confidence">
        <span className="approval-card__label">Confidence: {confidencePercent}%</span>
        <div className="approval-card__bar">
          <div
            className="approval-card__bar-fill"
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Rationale */}
      {action.rationale && (
        <div className="approval-card__rationale">{action.rationale}</div>
      )}

      {/* Timer */}
      {timeLeft != null && timeLeft > 0 && (
        <div className="approval-card__timer">
          Expires in {timeLeft} min
        </div>
      )}

      {/* Actions */}
      {action.status === 'reviewing' && (
        <div className="approval-card__actions">
          <button
            className="approval-card__btn approval-card__btn--approve"
            onClick={(e) => { e.stopPropagation(); handleApprove(); }}
            disabled={isProcessing || action.isLifeSafety}
          >
            {action.isLifeSafety ? 'Blocked (Safety)' : 'Approve'}
          </button>
          <button
            className="approval-card__btn approval-card__btn--reject"
            onClick={(e) => { e.stopPropagation(); handleReject(); }}
            disabled={isProcessing}
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
