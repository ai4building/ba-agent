// ============================================================
// HmiCanvas — Interactive SVG HMI canvas with live data binding
// ============================================================

import { useState, useMemo } from 'react';
import { HmiCanvasRenderer } from '../../core/HmiCanvasRenderer';
import type { HmiLayout, HmiWidget } from '../../types';
import './HmiCanvas.css';

interface HmiCanvasProps {
  layout: HmiLayout;
  activePage?: number;
  onWidgetClick?: (widget: HmiWidget) => void;
  /** Map of pointId → current value, injected by parent via watch */
  pointValues?: Record<string, number | string | boolean>;
  /** Map of pointId → unit string */
  pointUnits?: Record<string, string>;
}

const CANVAS_WIDTH = 960;
const CANVAS_HEIGHT = 640;

export function HmiCanvas({
  layout,
  activePage = 0,
  onWidgetClick,
  pointValues = {},
  pointUnits = {},
}: HmiCanvasProps) {
  const [selectedWidgetId, setSelectedWidgetId] = useState<string | null>(null);
  const [hoveredWidgetId, setHoveredWidgetId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(activePage);

  const page = layout.pages[currentPage];
  if (!page) return <div className="hmi-canvas__empty">No pages in layout</div>;

  const widgets = useMemo(() => {
    return page.widgets.map((widget) => {
      const coords = HmiCanvasRenderer.mapToSvg(widget, page, {
        width: CANVAS_WIDTH,
        height: CANVAS_HEIGHT,
      });
      const WidgetComponent = HmiCanvasRenderer.resolveWidget(widget.widget_type);
      return { widget, coords, WidgetComponent };
    });
  }, [page]);

  const handleWidgetClick = (widget: HmiWidget) => {
    setSelectedWidgetId(widget.id === selectedWidgetId ? null : widget.id);
    onWidgetClick?.(widget);
  };

  return (
    <div className="hmi-canvas">
      {/* Page tabs */}
      {layout.pages.length > 1 && (
        <div className="hmi-canvas__tabs">
          {layout.pages.map((p, i) => (
            <button
              key={p.id}
              className={`hmi-canvas__tab ${i === currentPage ? 'hmi-canvas__tab--active' : ''}`}
              onClick={() => setCurrentPage(i)}
            >
              {p.title}
            </button>
          ))}
        </div>
      )}

      {/* SVG Canvas */}
      <svg
        className="hmi-canvas__svg"
        viewBox={`0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Background grid */}
        <defs>
          <pattern
            id="grid" width={CANVAS_WIDTH / page.grid_columns}
            height={CANVAS_HEIGHT / page.grid_rows}
            patternUnits="userSpaceOnUse"
          >
            <rect
              width={CANVAS_WIDTH / page.grid_columns}
              height={CANVAS_HEIGHT / page.grid_rows}
              fill="none" stroke="rgba(148,163,184,0.08)" strokeWidth={0.5}
            />
          </pattern>
        </defs>
        <rect width={CANVAS_WIDTH} height={CANVAS_HEIGHT} fill="url(#grid)" />

        {/* Widgets */}
        {widgets.map(({ widget, coords, WidgetComponent }) => (
          <g
            key={widget.id}
            onMouseEnter={() => setHoveredWidgetId(widget.id)}
            onMouseLeave={() => setHoveredWidgetId(null)}
          >
            <WidgetComponent
              x={coords.x}
              y={coords.y}
              width={coords.width}
              height={coords.height}
              label={widget.label}
              pointId={widget.point_id}
              currentValue={pointValues[widget.point_id]}
              unit={pointUnits[widget.point_id]}
              onClick={() => handleWidgetClick(widget)}
              isSelected={widget.id === selectedWidgetId}
            />
          </g>
        ))}

        {/* Tooltip */}
        {hoveredWidgetId && (() => {
          const hovered = widgets.find((w) => w.widget.id === hoveredWidgetId);
          if (!hovered) return null;
          const { widget, coords } = hovered;
          const val = pointValues[widget.point_id];
          const tooltipX = coords.x + coords.width / 2;
          const tooltipY = coords.y - 8;

          return (
            <g>
              <rect
                x={tooltipX - 60} y={tooltipY - 28} width={120} height={24}
                rx={4} fill="rgba(15,23,42,0.95)" stroke="rgba(148,163,184,0.3)" strokeWidth={0.5}
              />
              <text x={tooltipX} y={tooltipY - 12} textAnchor="middle" fill="#e2e8f0" fontSize={10}>
                {widget.point_id}: {val != null ? String(val) : 'N/A'}
              </text>
            </g>
          );
        })()}
      </svg>

      {/* Page info */}
      <div className="hmi-canvas__info">
        <span>{page.title}</span>
        <span className="hmi-canvas__info-meta">
          {page.grid_columns}×{page.grid_rows} grid · {page.widgets.length} widgets
        </span>
      </div>
    </div>
  );
}
