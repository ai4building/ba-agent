// ============================================================
// TrendWidget — Mini trend line SVG widget
// ============================================================

import type { SvgWidgetProps } from '../../../types';

// Generate a simple sine-like trend for demo; in production, use real hisRead data
function generateDemoPoints(x: number, y: number, w: number, h: number, value: number): string {
  const points: string[] = [];
  const steps = 20;
  const padY = 16;
  const padX = 4;
  const graphH = h - padY * 2;
  const graphW = w - padX * 2;
  const baseVal = typeof value === 'number' ? (value % 40) : 20;

  for (let i = 0; i <= steps; i++) {
    const px = x + padX + (i / steps) * graphW;
    const noise = Math.sin(i * 0.8 + baseVal) * 0.3 + Math.cos(i * 0.3) * 0.15;
    const py = y + padY + graphH * (0.5 - noise * 0.5);
    points.push(`${px},${py}`);
  }
  return points.join(' ');
}

export function TrendWidget({
  x, y, width, height, label, currentValue, unit, onClick, isSelected,
}: SvgWidgetProps) {
  const numVal = typeof currentValue === 'number' ? currentValue : 0;
  const polyPoints = generateDemoPoints(x, y, width, height, numVal);

  return (
    <g onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <rect
        x={x} y={y} width={width} height={height}
        rx={4} fill={isSelected ? 'rgba(59,130,246,0.15)' : 'rgba(30,41,59,0.6)'}
        stroke={isSelected ? '#3b82f6' : 'rgba(148,163,184,0.2)'} strokeWidth={1}
      />
      {/* Trend line */}
      <polyline
        points={polyPoints}
        fill="none" stroke="#10b981" strokeWidth={1.5} strokeLinejoin="round"
      />
      {/* Current value */}
      <text x={x + width - 8} y={y + 14} textAnchor="end" fill="#e2e8f0" fontSize={11} fontWeight={600}>
        {typeof currentValue === 'number' ? currentValue.toFixed(1) : '--'}{unit ? ` ${unit}` : ''}
      </text>
      {/* Label */}
      <text x={x + 8} y={y + height - 6} fill="#94a3b8" fontSize={10}>
        {label}
      </text>
    </g>
  );
}
