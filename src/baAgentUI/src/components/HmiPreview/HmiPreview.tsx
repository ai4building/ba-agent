// ============================================================
// HmiPreview Component - Modern HMI layout preview
// ============================================================

import { Layout, Grid3x3, TrendingUp, Activity, Gauge, Settings, MonitorPlay } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter } from '../ui';
import { Badge } from '../ui';
import { Button } from '../ui';
import { cn } from '../../utils/cn';
import { useState } from 'react';
import type { HmiLayout as HmiLayoutType } from '../../types';
import './HmiPreview.css';

const WIDGET_ICONS: Record<string, React.ReactNode> = {
  gauge: <Gauge size={16} />,
  trend: <TrendingUp size={16} />,
  status: <MonitorPlay size={16} />,
  setpoint: <Settings size={16} />,
  alarm: <Activity size={16} />,
  number: <Grid3x3 size={16} />,
};

interface HmiPreviewProps {
  layout: HmiLayoutType;
  onConfirm?: (layout: HmiLayoutType) => void;
  onAdjust?: (layout: HmiLayoutType) => void;
  onLivePreview?: (layout: HmiLayoutType) => void;
}

export function HmiPreview({ layout, onConfirm, onAdjust, onLivePreview }: HmiPreviewProps) {
  const [activePage, setActivePage] = useState(0);
  const [hoveredWidget, setHoveredWidget] = useState<string | null>(null);

  const currentPage = layout.pages[activePage];

  const handleConfirm = () => {
    onConfirm?.(layout);
  };

  const handleAdjust = () => {
    onAdjust?.(layout);
  };

  return (
    <Card variant="glass" className="hmi-preview">
      <CardHeader className="hmi-header">
        <div className="hmi-title-section">
          <div className="hmi-icon">
            <Layout size={24} />
          </div>
          <div className="hmi-info">
            <h3 className="hmi-title">HMI 布局预览</h3>
            {/* layout has no device property, showing total_pages instead */}
            <p className="hmi-subtitle">{layout.total_pages} 页面 / {layout.total_widgets} 组件</p>
          </div>
        </div>

        <div className="hmi-stats">
          <div className="hmi-stat">
            <span className="stat-value">{layout.total_pages}</span>
            <span className="stat-label">页面</span>
          </div>
          <div className="hmi-stat">
            <span className="stat-value">{layout.total_widgets}</span>
            <span className="stat-label">组件</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="hmi-content">
        {/* Page Tabs */}
        {layout.pages.length > 1 && (
          <div className="hmi-tabs">
            {layout.pages.map((page, tabIndex) => (
              <button
                key={page.id}
                className={cn('hmi-tab', activePage === tabIndex && 'hmi-tab-active')}
                onClick={() => setActivePage(tabIndex)}
              >
                {page.title}
                {activePage === tabIndex && <span className="tab-indicator" />}
              </button>
            ))}
          </div>
        )}

        {/* Page Content */}
        {currentPage && (
          <div className="hmi-page">
            <div className="page-meta">
              <Badge variant="purple">{currentPage.equip_type}</Badge>
              <span className="page-grid-info">
                {currentPage.grid_columns} × {currentPage.grid_rows}
              </span>
            </div>

            {/* Widget Grid Preview */}
            <div
              className="widget-grid-preview"
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${currentPage.grid_columns}, 1fr)`,
                gridTemplateRows: `repeat(${currentPage.grid_rows}, 1fr)`,
                gap: '8px',
              }}
            >
              {currentPage.widgets.map((widget) => (
                <div
                  key={widget.id}
                  className={cn(
                    'widget-preview-item',
                    `widget-type-${widget.widget_type}`,
                    hoveredWidget === widget.id && 'widget-hovered'
                  )}
                  style={{
                    gridColumn: `${widget.col + 1} / span ${widget.col_span || 1}`,
                    gridRow: `${widget.row + 1} / span ${widget.row_span || 1}`,
                  }}
                  onMouseEnter={() => setHoveredWidget(widget.id)}
                  onMouseLeave={() => setHoveredWidget(null)}
                >
                  <div className="widget-icon">{WIDGET_ICONS[widget.widget_type] || <div className="widget-icon-dot" />}</div>
                  <div className="widget-details">
                    <span className="widget-label">{widget.label}</span>
                    {widget.point_id && (
                      <span className="widget-binding">{widget.point_id}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Widget List */}
            <div className="widget-list-section">
              <h4 className="widget-list-title">
                <Grid3x3 size={14} />
                组件列表 ({currentPage.widgets.length})
              </h4>
              <div className="widget-list">
                {currentPage.widgets.map((widget) => (
                  <div key={widget.id} className="widget-list-item">
                    <div className="widget-type-badge">
                      {WIDGET_ICONS[widget.widget_type] || <div className="widget-icon-dot" />}
                      <span>{widget.widget_type}</span>
                    </div>
                    <span className="widget-name">{widget.label}</span>
                    <div className="widget-position">
                      <span className="widget-coords">({widget.row + 1}, {widget.col + 1})</span>
                      {(widget.row_span! > 1 || widget.col_span! > 1) && (
                        <span className="widget-span"> — {widget.row_span}×{widget.col_span}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Navigation Structure */}
        {layout.navigation && layout.navigation.length > 0 && (
          <div className="hmi-navigation">
            <h4 className="nav-title">导航结构</h4>
            <div className="nav-items">
              {layout.navigation.map((nav) => (
                <div key={nav.id} className="nav-item">
                  {nav.icon && <span className="nav-icon">{nav.icon}</span>}
                  <span className="nav-label">{nav.label}</span>
                  <span className="nav-arrow">→</span>
                  <span className="nav-target">{nav.target_page}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="hmi-footer">
        <Button variant="secondary" onClick={handleAdjust}>
          <Settings size={16} />
          调整布局
        </Button>
        {onLivePreview && (
          <Button variant="secondary" onClick={() => onLivePreview(layout)}>
            <MonitorPlay size={16} />
            实时预览
          </Button>
        )}
        <Button variant="primary" onClick={handleConfirm}>
          <Layout size={16} />
          确认发布
        </Button>
      </CardFooter>
    </Card>
  );
}
