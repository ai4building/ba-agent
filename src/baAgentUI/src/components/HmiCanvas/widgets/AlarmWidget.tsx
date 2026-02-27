// ============================================================
// AlarmWidget — Alarm status indicator SVG widget
// ============================================================

import type { SvgWidgetProps } from '../../../types';

export function AlarmWidget({
  x, y, width, height, label, currentValue, onClick, isSelected,
}: SvgWidgetProps) {
  const isActive = currentValue === true || currentValue === 'active' || currentValue === 1;
  const cx = x + width / 2;
  const cy = y + height / 2 - 6;

  return (
    <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <rect
        x={x} y={y} width={width} height={height}
        rx={4} fill={isSelected ? 'rgba(59,130,246,0.15)' : isActive ? 'rgba(127,29,29,0.3)' : 'rgba(30,41,59,0.6)'}
        stroke={isSelected ? '#3b82f6' : isActive ? 'rgba(239,68,68,0.5)' : 'rgba(148,163,184,0.2)'} strokeWidth={1}
      />
      {/* Bell icon */}
      <path
        d={`M ${cx - 8} ${cy + 2} C ${cx - 8} ${cy - 8}, ${cx + 8} ${cy - 8}, ${cx + 8} ${cy + 2} L ${cx + 10} ${cy + 6} L ${cx - 10} ${cy + 6} Z`}
        fill={isActive ? '#ef4444' : '#64748b'}
      />
      <circle cx={cx} cy={cy + 9} r={2.5} fill={isActive ? '#ef4444' : '#64748b'} />
      {/* Status text */}
      <text x={cx} y={cy + 24} textAnchor="middle" fill={isActive ? '#ef4444' : '#94a3b8'} fontSize={10} fontWeight={600}>
        {isActive ? 'ALARM' : 'Normal'}
      </text>
      {/* Label */}
      <text x={cx} y={y + height - 6} textAnchor="middle" fill="#94a3b8" fontSize={10}>
        {label}
      </text>
    </g>
  );
}
