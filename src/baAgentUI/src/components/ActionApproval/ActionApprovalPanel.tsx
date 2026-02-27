// ============================================================
// ActionApprovalPanel — Aggregated AI action approval panel
// ============================================================

import { ActionApprovalCard } from './ActionApprovalCard';
import type { PendingAiAction, AuditLogEntry } from '../../types';
import './ActionApprovalPanel.css';

interface ActionApprovalPanelProps {
  pendingActions: PendingAiAction[];
  auditLog: AuditLogEntry[];
  onApprove: (actionId: string) => void;
  onReject: (actionId: string) => void;
  onStartReview: (actionId: string) => void;
}

export function ActionApprovalPanel({
  pendingActions,
  auditLog,
  onApprove,
  onReject,
  onStartReview,
}: ActionApprovalPanelProps) {
  if (pendingActions.length === 0 && auditLog.length === 0) {
    return null;
  }

  return (
    <div className="approval-panel">
      {/* Pending actions */}
      {pendingActions.length > 0 && (
        <div className="approval-panel__section">
          <h3 className="approval-panel__title">
            Pending AI Actions
            <span className="approval-panel__badge">{pendingActions.length}</span>
          </h3>
          <div className="approval-panel__list">
            {pendingActions.map((action) => (
              <ActionApprovalCard
                key={action.id}
                action={action}
                onApprove={onApprove}
                onReject={onReject}
                onStartReview={onStartReview}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent audit log */}
      {auditLog.length > 0 && (
        <div className="approval-panel__section">
          <h3 className="approval-panel__title">Recent Audit Log</h3>
          <div className="approval-panel__log">
            {auditLog.slice(-10).reverse().map((entry) => (
              <div key={`${entry.actionId}-${entry.timestamp.getTime()}`} className="approval-panel__log-entry">
                <span
                  className={`approval-panel__log-decision approval-panel__log-decision--${entry.decision}`}
                >
                  {entry.decision === 'approved' ? '&#10003;' : '&#10007;'}
                </span>
                <span className="approval-panel__log-point">{entry.pointId}</span>
                <span className="approval-panel__log-values">
                  {entry.previousValue} &#8594; {entry.newValue}
                </span>
                <span className="approval-panel__log-time">
                  {entry.timestamp.toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
