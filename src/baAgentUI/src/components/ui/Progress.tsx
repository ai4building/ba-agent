// ============================================================
// Progress Component - Progress bars and meters
// ============================================================

import { forwardRef } from 'react';
import { cn } from '../../utils/cn';

export interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'gradient';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

export const ProgressBar = forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ value, max = 100, size = 'md', variant = 'default', showLabel, label, className }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
      <div ref={ref} className={cn('progress-container', `progress-${size}`, className)}>
        {(showLabel || label) && (
          <div className="progress-label">
            {label || `${percentage}%`}
          </div>
        )}
        <div className="progress-track">
          <div
            className={cn('progress-fill', `progress-${variant}`)}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }
);

ProgressBar.displayName = 'ProgressBar';

export interface CircularProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  children?: React.ReactNode;
}

export const CircularProgress = forwardRef<HTMLDivElement, CircularProgressProps>(
  ({ value, max = 100, size = 40, strokeWidth = 4, variant = 'default', children }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percentage / 100) * circumference;

    return (
      <div ref={ref} className="circular-progress" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="progress-ring">
          <circle
            className="progress-ring-bg"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            className={cn('progress-ring-fill', `progress-${variant}`)}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: offset,
            }}
          />
        </svg>
        {children && <div className="progress-content">{children}</div>}
      </div>
    );
  }
);

CircularProgress.displayName = 'CircularProgress';
