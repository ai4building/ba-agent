// ============================================================
// Badge Component - Status and label badges
// ============================================================

import { forwardRef } from 'react';
import { cn } from '../../utils/cn';

export interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'blue';
  size?: 'sm' | 'md';
  dot?: boolean;
  children: React.ReactNode;
  class?: string;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ class: className, variant = 'default', size = 'md', dot, children }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          'badge',
          `badge-${variant}`,
          `badge-${size}`,
          dot && 'badge-dot',
          className
        )}
      >
        {dot && <span className="badge-dot-indicator" />}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';
