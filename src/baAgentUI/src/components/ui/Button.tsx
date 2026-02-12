// ============================================================
// Button Component
// ============================================================

import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'ref'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, onClick, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'button',
          `button-${variant}`,
          `button-${size}`,
          isLoading && 'button-loading',
          className
        )}
        disabled={disabled || isLoading}
        onClick={onClick}
        {...props}
      >
        {isLoading ? (
          <span className="button-spinner" />
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
