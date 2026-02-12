// ============================================================
// AlarmBanner Component
// Displays active alarm count using useAlarmWatch hook
// ============================================================

import { useAlarmWatch } from '../../hooks/useAlarmWatch';
import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';
import './AlarmBanner.css';

export function AlarmBanner() {
  const { alarms, alarmCount, criticalCount, warningCount, isLoading } =
    useAlarmWatch({ pollRate: 5 });

  const [dismissed, setDismissed] = useState(false);

  // Don't show if no alarms, loading, or dismissed
  if (alarmCount === 0 || isLoading || dismissed) {
    return null;
  }

  const hasCritical = criticalCount > 0;

  return (
    <div className={`alarm-banner ${hasCritical ? 'alarm-critical' : 'alarm-warning'}`}>
      <div className="alarm-banner-content">
        <AlertTriangle size={20} className="alarm-icon" />
        <div className="alarm-summary">
          <span className="alarm-count">
            {alarmCount} Active Alarm{alarmCount > 1 ? 's' : ''}
          </span>
          <span className="alarm-details">
            {criticalCount > 0 && (
              <span className="alarm-critical-count">
                {criticalCount} Critical
              </span>
            )}
            {warningCount > 0 && (
              <span className="alarm-warning-count">
                {warningCount} Warning
              </span>
            )}
          </span>
        </div>
        <button
          className="alarm-dismiss"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss alarm banner"
        >
          <X size={16} />
        </button>
      </div>

      {/* Quick alarm preview - show top 3 */}
      {alarms.slice(0, 3).length > 0 && (
        <div className="alarm-preview">
          {alarms.slice(0, 3).map((alarm) => (
            <div key={alarm.id} className="alarm-preview-item">
              <span
                className={`alarm-dot severity-${alarm.severity}`}
              />
              <span className="alarm-text">{alarm.dis}</span>
            </div>
          ))}
          {alarmCount > 3 && (
            <div className="alarm-more">
              +{alarmCount - 3} more
            </div>
          )}
        </div>
      )}
    </div>
  );
}
