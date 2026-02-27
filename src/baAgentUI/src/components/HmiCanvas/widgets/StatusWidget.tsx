// ============================================================
// StatusWidget — On/Off status indicator SVG widget
// ============================================================

import type { SvgWidgetProps } from '../../../types';

export function StatusWidget({
  x, y, width, height, label, currentValue, onClick, isSelected,
}: SvgWidgetProps) {
  const isOn = currentValue === true || currentValue === 'on' || currentValue === 1;
  const cx = x + width / 2;
  const cy = y + height / 2 - 4;

  return (
    <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <rect
        x={x} y={y} width={width} height={height}
        rx={4} fill={isSelected ? 'rgba(59,130,246,0.15)' : 'rgba(30,41,59,0.6)'}
        stroke={isSelected ? '#3b82f6' : 'rgba(148,163,184,0.2)'} strokeWidth={1}
      />
      {/* Status indicator circle */}
      <circle
        cx={cx} cy={cy} r={10}
        fill={isOn ? '#10b981' : '#64748b'}
        opacity={0.9}
      />
      {/* Glow ring */}
      <circle
        cx={cx} cy={cy} r={14}
        fill="none" stroke={isOn ? '#10b981' : '#64748b'}
        strokeWidth={1} opacity={0.3}
      />
      {/* Status text */}
      <text x={cx} y={cy + 28} textAnchor="middle" fill={isOn ? '#10b981' : '#94a3b8'} fontSize={11} fontWeight={600}>
        {isOn ? 'ON' : 'OFF'}
      </text>
      {/* Label */}
      <text x={cx} y={y + height - 6} textAnchor="middle" fill="#94a3b8" fontSize={10}>
        {label}
      </text>
    </g>
  );
}
