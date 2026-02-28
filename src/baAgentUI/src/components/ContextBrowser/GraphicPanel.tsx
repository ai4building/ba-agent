// ============================================================
// GraphicPanel — Graphic viewer via iframe or point summary
// ============================================================

import { useState } from 'react';
import { Maximize2, X, Loader2, Image, CircleDot } from 'lucide-react';
import type { NavNode } from '../../types';

interface GraphicPanelProps {
  selectedNode: NavNode | null;
  graphicUrl: string | null;
  graphicDis: string | null;
  graphicLoading: boolean;
  graphicError: string | null;
  childPoints: NavNode[];
}

export function GraphicPanel({
  selectedNode,
  graphicUrl,
  graphicDis,
  graphicLoading,
  graphicError,
  childPoints,
}: GraphicPanelProps) {
  const [fullscreen, setFullscreen] = useState(false);

  if (!selectedNode) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        padding: '24px', color: '#475569', fontSize: '11px', textAlign: 'center', gap: '8px',
      }}>
        <Image size={24} style={{ color: '#334155' }} />
        <span>选择设备查看监控画面</span>
      </div>
    );
  }

  if (graphicLoading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px', color: '#64748b', gap: '8px', fontSize: '11px',
      }}>
        <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
        加载画面...
      </div>
    );
  }

  if (graphicError) {
    return (
      <div style={{ padding: '12px', color: '#f87171', fontSize: '11px' }}>
        加载失败: {graphicError}
      </div>
    );
  }

  // Graphic iframe view
  if (graphicUrl) {
    return (
      <>
        <div style={{ position: 'relative' }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 8px', backgroundColor: 'rgba(30, 41, 59, 0.5)',
            borderBottom: '1px solid #1e293b',
          }}>
            <span style={{ fontSize: '10px', color: '#94a3b8' }}>
              {graphicDis ?? 'Graphic'}
            </span>
            <button
              onClick={() => setFullscreen(true)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#64748b', padding: '2px', display: 'flex',
              }}
              title="全屏查看"
            >
              <Maximize2 size={12} />
            </button>
          </div>
          <iframe
            src={graphicUrl}
            style={{
              width: '100%', height: '180px', border: 'none',
              backgroundColor: '#0f172a',
            }}
            title={graphicDis ?? 'Equipment Graphic'}
          />
        </div>

        {/* Fullscreen modal */}
        {fullscreen && (
          <div style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            backgroundColor: 'rgba(0,0,0,0.85)',
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 20px', backgroundColor: '#0f172a',
              borderBottom: '1px solid #1e293b',
            }}>
              <span style={{ color: '#e2e8f0', fontSize: '14px', fontWeight: 'bold' }}>
                {graphicDis ?? selectedNode.dis}
              </span>
              <button
                onClick={() => setFullscreen(false)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: '#94a3b8', padding: '4px', display: 'flex',
                }}
              >
                <X size={20} />
              </button>
            </div>
            <iframe
              src={graphicUrl}
              style={{ flex: 1, border: 'none', backgroundColor: '#0f172a' }}
              title={graphicDis ?? 'Equipment Graphic'}
            />
          </div>
        )}
      </>
    );
  }

  // No graphic — show point summary
  if (childPoints.length > 0) {
    return (
      <div style={{ padding: '8px' }}>
        <div style={{
          fontSize: '10px', color: '#64748b', textTransform: 'uppercase',
          letterSpacing: '0.05em', marginBottom: '6px', padding: '0 4px',
        }}>
          点位概览 ({childPoints.length})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '160px', overflowY: 'auto' }}>
          {childPoints.slice(0, 20).map(pt => (
            <div
              key={pt.id}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '4px 8px', borderRadius: '4px',
                backgroundColor: 'rgba(30, 41, 59, 0.3)',
                fontSize: '11px',
              }}
            >
              <span style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CircleDot size={10} style={{ color: '#fbbf24' }} />
                {pt.dis}
              </span>
              {pt.curVal !== undefined && (
                <span style={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '10px' }}>
                  {typeof pt.curVal === 'boolean' ? (pt.curVal ? 'ON' : 'OFF') : pt.curVal}
                  {pt.unit ? ` ${pt.unit}` : ''}
                </span>
              )}
            </div>
          ))}
          {childPoints.length > 20 && (
            <div style={{ fontSize: '10px', color: '#475569', textAlign: 'center', padding: '4px' }}>
              ... 还有 {childPoints.length - 20} 个点位
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      padding: '16px', color: '#475569', fontSize: '11px', textAlign: 'center',
    }}>
      该设备暂无关联画面或点位
    </div>
  );
}
