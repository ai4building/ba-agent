// ============================================================
// GaugeWidget — Circular gauge SVG widget
// ============================================================

import type { SvgWidgetProps } from '../../../types';

export function GaugeWidget({
  x, y, width, height, label, currentValue, unit, onClick, isSelected,
}: SvgWidgetProps) {
  const cx = x + width / 2;
  const cy = y + height / 2;
  const radius = Math.min(width, height) / 2 - 8;
  const numVal = typeof currentValue === 'number' ? currentValue : 0;

  // Gauge arc: 0-100 mapped to 180° arc (-180 to 0 degrees)
  const normalized = Math.min(Math.max(numVal / 100, 0), 1);
  const startAngle = -Math.PI;
  const endAngle = startAngle + normalized * Math.PI;

  const arcX = cx + radius * Math.cos(endAngle);
  const arcY = cy + radius * Math.sin(endAngle);
  const largeArc = normalized > 0.5 ? 1 : 0;

  const arcPath = `M ${cx - radius} ${cy} A ${radius} ${radius} 0 ${largeArc} 1 ${arcX} ${arcY}`;

  return (
    <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <rect
        x={x} y={y} width={width} height={height}
        rx={4} fill={isSelected ? 'rgba(59,130,246,0.15)' : 'rgba(30,41,59,0.6)'}
        stroke={isSelected ? '#3b82f6' : 'rgba(148,163,184,0.2)'} strokeWidth={1}
      />
      {/* Background arc */}
      <path
        d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 1 1 ${cx + radius} ${cy}`}
        fill="none" stroke="rgba(148,163,184,0.2)" strokeWidth={6} strokeLinecap="round"
      />
      {/* Value arc */}
      <path
        d={arcPath}
        fill="none" stroke="#3b82f6" strokeWidth={6} strokeLinecap="round"
      />
      {/* Value text */}
      <text x={cx} y={cy + 4} textAnchor="middle" fill="#e2e8f0" fontSize={14} fontWeight={600}>
        {typeof currentValue === 'number' ? currentValue.toFixed(1) : '--'}
      </text>
      {/* Unit */}
      <text x={cx} y={cy + 18} textAnchor="middle" fill="#94a3b8" fontSize={9}>
        {unit ?? ''}
      </text>
      {/* Label */}
      <text x={cx} y={y + height - 6} textAnchor="middle" fill="#94a3b8" fontSize={10}>
        {label}
      </text>
    </g>
  );
}
