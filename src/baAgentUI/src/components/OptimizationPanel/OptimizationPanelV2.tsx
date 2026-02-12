// ============================================================
// OptimizationPanel Component V2
// Enhanced with useSetpointControl for bidirectional point control
// ============================================================

import type { OptimizationData } from '../../types';
import { useSetpointControls, formatTemperature } from '../../hooks';
import { Zap, TrendingDown, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { useState } from 'react';
import './OptimizationPanelV2.css';

interface OptimizationPanelProps {
  optimization: OptimizationData;
  onApply?: (optimization: OptimizationData) => void;
  onCancel?: () => void;
}

export function OptimizationPanelV2({
  optimization,
  onApply,
  onCancel,
}: OptimizationPanelProps) {
  const { current_energy, predicted_savings, savings_percent, setpoints, rationale } =
    optimization;

  // Get point IDs for setpoint control
  const pointIds = setpoints.map((sp) => sp.point_id);

  // Use useSetpointControls for bidirectional control
  const { controls, isLoading } = useSetpointControls(pointIds);

  const [selectedSetpoints, setSelectedSetpoints] = useState<Set<string>>(new Set());

  // Toggle setpoint selection
  const toggleSetpoint = (pointId: string) => {
    setSelectedSetpoints((prev) => {
      const next = new Set(prev);
      if (next.has(pointId)) {
        next.delete(pointId);
      } else {
        next.add(pointId);
      }
      return next;
    });
  };

  // Select/deselect all
  const toggleAll = () => {
    if (selectedSetpoints.size === setpoints.length) {
      setSelectedSetpoints(new Set());
    } else {
      setSelectedSetpoints(new Set(setpoints.map((sp) => sp.point_id)));
    }
  };

  // Apply selected recommendations
  const handleApplySelected = async () => {
    const recommendations = setpoints.filter((sp) =>
      selectedSetpoints.has(sp.point_id)
    );

    for (const rec of recommendations) {
      const control = controls.get(rec.point_id);
      if (control) {
        await control.applyRecommendation(rec.recommended_value);
      }
    }

    onApply?.(optimization);
  };

  // Apply a single setpoint
  const handleApplySingle = async (pointId: string) => {
    const control = controls.get(pointId);
    const setpoint = setpoints.find((sp) => sp.point_id === pointId);

    if (control && setpoint) {
      await control.applyRecommendation(setpoint.recommended_value);
    }
  };

  const hasSelections = selectedSetpoints.size > 0;
  const allSelected = selectedSetpoints.size === setpoints.length;

  return (
    <div className="optimization-panel-v2">
      {/* Header with savings highlight */}
      <div className="optimization-header">
        <div className="optimization-icon">
          <Zap size={24} />
        </div>
        <div className="optimization-summary">
          <h3>Energy Optimization Opportunity</h3>
          <div className="savings-highlight">
            <TrendingDown size={18} />
            <span className="savings-value">{savings_percent.toFixed(1)}%</span>
            <span className="savings-label">potential savings</span>
          </div>
          <div className="savings-amount">
            ${predicted_savings.toFixed(2)}/year estimated
          </div>
        </div>
      </div>

      {/* Rationale */}
      {rationale && (
        <div className="optimization-rationale">
          <h4>Analysis</h4>
          <p>{rationale}</p>
        </div>
      )}

      {/* Current energy consumption */}
      <div className="energy-current">
        <span className="energy-label">Current annual consumption:</span>
        <span className="energy-value">{current_energy.toLocaleString()} kWh</span>
      </div>

      {/* Selection controls */}
      <div className="selection-controls">
        <label className="select-all-checkbox">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
          />
          <span>Select all ({setpoints.length})</span>
        </label>
        <span className="selected-count">
          {hasSelections ? `${selectedSetpoints.size} selected` : 'None selected'}
        </span>
      </div>

      {/* Setpoint recommendations */}
      {setpoints.length > 0 && (
        <div className="setpoints-list">
          {setpoints.map((setpoint) => {
            const control = controls.get(setpoint.point_id);
            const isSelected = selectedSetpoints.has(setpoint.point_id);

            return (
              <SetpointRow
                key={setpoint.point_id}
                setpoint={setpoint}
                currentActualValue={control?.currentValue}
                isApplying={control?.isApplying || false}
                hasPendingChange={control?.hasPendingChange || false}
                isSelected={isSelected}
                onSelect={() => toggleSetpoint(setpoint.point_id)}
                onApply={() => handleApplySingle(setpoint.point_id)}
              />
            );
          })}
        </div>
      )}

      {/* Actions */}
      <div className="optimization-actions">
        <button
          className="apply-btn"
          onClick={handleApplySelected}
          disabled={!hasSelections || isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 size={18} className="spinner" />
              Applying...
            </>
          ) : (
            <>
              <CheckCircle2 size={18} />
              Apply Selected ({selectedSetpoints.size})
            </>
          )}
        </button>
        <button className="cancel-btn" onClick={onCancel}>
          <XCircle size={18} />
          Discard
        </button>
      </div>
    </div>
  );
}

interface SetpointRowProps {
  setpoint: {
    point_id: string;
    point_name: string;
    current_value: number;
    recommended_value: number;
    unit: string;
    priority: 'high' | 'medium' | 'low';
  };
  currentActualValue?: number;
  isApplying?: boolean;
  hasPendingChange?: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
  onApply?: () => void;
}

function SetpointRow({
  setpoint,
  currentActualValue,
  isApplying,
  hasPendingChange,
  isSelected,
  onSelect,
  onApply,
}: SetpointRowProps) {
  const { point_name, current_value, recommended_value, unit, priority } = setpoint;

  // Use actual current value from live data if available
  const displayCurrentValue = currentActualValue ?? current_value;
  const diff = recommended_value - displayCurrentValue;
  const isIncrease = diff > 0;
  const isTemp = unit.includes('C') || unit.includes('F');

  return (
    <div
      className={`setpoint-row priority-${priority} ${isSelected ? 'selected' : ''}`}
    >
      <div className="setpoint-select">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          aria-label={`Select ${point_name}`}
        />
      </div>

      <div className="setpoint-info">
        <div className="setpoint-name">{point_name}</div>
        <div className="setpoint-priority">{priority} priority</div>
      </div>

      <div className="setpoint-values">
        <div className="value-current">
          <span className="value-label">Current</span>
          <span className="value-number">
            {isTemp
              ? formatTemperature(displayCurrentValue, unit)
              : `${displayCurrentValue.toFixed(1)} ${unit}`}
          </span>
        </div>

        <div className="value-arrow">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d={isIncrease ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
          </svg>
        </div>

        <div className="value-recommended">
          <span className="value-label">Recommended</span>
          <span className="value-number recommended">
            {isTemp
              ? formatTemperature(recommended_value, unit)
              : `${recommended_value.toFixed(1)} ${unit}`}
          </span>
        </div>
      </div>

      <div className="setpoint-change">
        {diff !== 0 && (
          <span className={isIncrease ? 'change-positive' : 'change-negative'}>
            {isIncrease ? '+' : ''}{diff.toFixed(1)}
          </span>
        )}
      </div>

      <div className="setpoint-actions">
        {hasPendingChange ? (
          <span className="pending-badge">Pending</span>
        ) : (
          <button
            className="apply-single-btn"
            onClick={onApply}
            disabled={isApplying}
            title="Apply this recommendation"
          >
            {isApplying ? (
              <Loader2 size={14} className="spinner" />
            ) : (
              <CheckCircle2 size={14} />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
