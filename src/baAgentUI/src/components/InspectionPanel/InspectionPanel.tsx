// ============================================================
// InspectionPanel Component
// Displays virtual inspection results for sensor health
// ============================================================

import type { InspectionData, SensorHealth } from '../../types';
import { Shield, ShieldAlert, ShieldX, Activity } from 'lucide-react';
import { cn } from '../../utils/cn';
import './InspectionPanel.css';

interface InspectionPanelProps {
  inspection: InspectionData;
}

export function InspectionPanel({ inspection }: InspectionPanelProps) {
  const { total_sensors, healthy_count, warning_count, failed_count, sensors } = inspection;

  const overallHealth = (healthy_count / total_sensors) * 100;

  return (
    <div className="inspection-panel">
      {/* Summary header */}
      <div className="inspection-summary">
        <div className={cn(
          'inspection-icon',
          overallHealth >= 80 ? 'health-good' : overallHealth >= 50 ? 'health-warning' : 'health-critical'
        )}>
          {overallHealth >= 80 ? <Shield size={28} /> :
           overallHealth >= 50 ? <ShieldAlert size={28} /> : <ShieldX size={28} />}
        </div>
        <div className="inspection-stats">
          <h3>Sensor Health Report</h3>
          <div className="health-score">
            <span className="score-value">{overallHealth.toFixed(0)}%</span>
            <span className="score-label">Overall Health</span>
          </div>
        </div>
        <div className="inspection-counters">
          <div className="counter healthy">
            <span className="counter-value">{healthy_count}</span>
            <span className="counter-label">Healthy</span>
          </div>
          <div className="counter warning">
            <span className="counter-value">{warning_count}</span>
            <span className="counter-label">Warning</span>
          </div>
          <div className="counter failed">
            <span className="counter-value">{failed_count}</span>
            <span className="counter-label">Failed</span>
          </div>
        </div>
      </div>

      {/* Health bar */}
      <div className="health-bar-container">
        <div className="health-bar">
          <div
            className="health-bar-fill healthy"
            style={{ width: `${(healthy_count / total_sensors) * 100}%` }}
          />
          <div
            className="health-bar-fill warning"
            style={{ width: `${(warning_count / total_sensors) * 100}%` }}
          />
          <div
            className="health-bar-fill failed"
            style={{ width: `${(failed_count / total_sensors) * 100}%` }}
          />
        </div>
      </div>

      {/* Sensor list */}
      <div className="sensors-list">
        <div className="sensors-header">
          <h4>Sensor Details</h4>
          <span className="sensors-count">{total_sensors} sensors inspected</span>
        </div>

        <div className="sensors-grid">
          {sensors.map((sensor) => (
            <SensorCard key={sensor.point_id} sensor={sensor} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SensorCard({ sensor }: { sensor: SensorHealth }) {
  const { point_name, health_score, status, findings, last_checked } = sensor;

  return (
    <div className={cn('sensor-card', `status-${status}`)}>
      <div className="sensor-header">
        <span className="sensor-name">{point_name}</span>
        <div className={cn(
          'health-badge',
          status === 'healthy' ? 'badge-healthy' :
          status === 'warning' ? 'badge-warning' : 'badge-failed'
        )}>
          <Activity size={12} />
          {health_score}%
        </div>
      </div>

      {findings.length > 0 && (
        <ul className="sensor-findings">
          {findings.map((finding, idx) => (
            <li key={idx}>{finding}</li>
          ))}
        </ul>
      )}

      <div className="sensor-footer">
        <span className="last-checked">
          Last checked: {new Date(last_checked).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
