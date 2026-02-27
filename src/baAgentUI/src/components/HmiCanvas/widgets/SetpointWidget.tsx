// ============================================================
// SetpointWidget — Setpoint value display SVG widget
// ============================================================

import type { SvgWidgetProps } from '../../../types';

export function SetpointWidget({
  x, y, width, height, label, currentValue, unit, onClick, isSelected,
}: SvgWidgetProps) {
  const cx = x + width / 2;
  const cy = y + height / 2;

  return (
    <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <rect
        x={x} y={y} width={width} height={height}
        rx={4} fill={isSelected ? 'rgba(59,130,246,0.15)' : 'rgba(30,41,59,0.6)'}
        stroke={isSelected ? '#3b82f6' : 'rgba(148,163,184,0.2)'} strokeWidth={1}
      />
      {/* Setpoint icon (target) */}
      <circle cx={cx} cy={cy - 10} r={12} fill="none" stroke="#f59e0b" strokeWidth={1.5} />
      <circle cx={cx} cy={cy - 10} r={6} fill="none" stroke="#f59e0b" strokeWidth={1.5} />
      <circle cx={cx} cy={cy - 10} r={2} fill="#f59e0b" />
      {/* Value */}
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#e2e8f0" fontSize={13} fontWeight={600}>
        {typeof currentValue === 'number' ? currentValue.toFixed(1) : '--'}
      </text>
      {/* Unit */}
      <text x={cx} y={cy + 24} textAnchor="middle" fill="#94a3b8" fontSize={9}>
        {unit ?? ''}
      </text>
      {/* Label */}
      <text x={cx} y={y + height - 6} textAnchor="middle" fill="#94a3b8" fontSize={10}>
        {label}
      </text>
    </g>
  );
}
