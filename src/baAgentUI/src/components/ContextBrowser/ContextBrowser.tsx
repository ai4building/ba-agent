// ============================================================
// ContextBrowser — Site/Equip/Point tree + Graphic preview
// ============================================================

import { useState, useMemo } from 'react';
import { Search, RefreshCw, ChevronDown, ChevronRight, FolderTree } from 'lucide-react';
import { useNavTree } from '../../hooks/useNavTree';
import { useGraphicViewer } from '../../hooks/useGraphicViewer';
import { NavTreeNode } from './NavTreeNode';
import { GraphicPanel } from './GraphicPanel';

interface ContextBrowserProps {
  onSelectEquip?: (equipId: string, equipDis: string) => void;
}

export function ContextBrowser({ onSelectEquip }: ContextBrowserProps) {
  const {
    rootIds, nodes, expanded, selectedId, selectedNode,
    loadingId, getChildren, toggleNode, selectNode, reload,
  } = useNavTree();

  const { graphicUrl, graphicDis, loading: graphicLoading, error: graphicError } =
    useGraphicViewer(selectedNode?.kind === 'equip' ? selectedNode.id : null);

  const [collapsed, setCollapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Handle node selection — notify parent for ContextWatcher integration
  const handleSelect = (id: string) => {
    selectNode(id);
    const node = nodes.get(id);
    if (node && (node.kind === 'equip' || node.kind === 'site')) {
      onSelectEquip?.(node.id, node.dis);
    }
  };

  // Filter root nodes by search
  const filteredRootIds = useMemo(() => {
    if (!searchTerm.trim()) return rootIds;
    const term = searchTerm.toLowerCase();
    // Search all loaded nodes
    const matchIds: string[] = [];
    for (const [id, node] of nodes) {
      if (node.dis.toLowerCase().includes(term)) {
        matchIds.push(id);
      }
    }
    return matchIds.length > 0 ? matchIds : rootIds;
  }, [rootIds, nodes, searchTerm]);

  // Get child points for selected equip (for point summary when no graphic)
  const childPoints = useMemo(() => {
    if (!selectedNode || selectedNode.kind !== 'equip') return [];
    return getChildren(selectedNode.id).filter(n => n.kind === 'point');
  }, [selectedNode, getChildren]);

  return (
    <section>
      {/* Header */}
      <h3
        onClick={() => setCollapsed(!collapsed)}
        style={{
          fontSize: '10px', fontWeight: 'bold', color: '#64748b',
          textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: collapsed ? '0' : '12px',
          display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <FolderTree size={12} />
        上下文浏览器
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </span>
      </h3>

      {!collapsed && (
        <div style={{
          backgroundColor: 'rgba(30, 41, 59, 0.3)', borderRadius: '12px',
          border: '1px solid #1e293b', overflow: 'hidden',
        }}>
          {/* Search + refresh bar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '6px 8px', borderBottom: '1px solid #1e293b',
          }}>
            <Search size={12} style={{ color: '#475569', flexShrink: 0 }} />
            <input
              type="text"
              placeholder="搜索设备..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{
                flex: 1, background: 'none', border: 'none', outline: 'none',
                color: '#e2e8f0', fontSize: '11px', padding: '2px 0',
              }}
            />
            <button
              onClick={reload}
              title="刷新"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#475569', padding: '2px', display: 'flex',
              }}
            >
              <RefreshCw size={12} />
            </button>
          </div>

          {/* Tree */}
          <div style={{ maxHeight: '240px', overflowY: 'auto', padding: '4px 0' }}>
            {filteredRootIds.length === 0 && loadingId === '' ? (
              <div style={{ padding: '12px', color: '#475569', fontSize: '11px', textAlign: 'center' }}>
                加载中...
              </div>
            ) : filteredRootIds.length === 0 ? (
              <div style={{ padding: '12px', color: '#475569', fontSize: '11px', textAlign: 'center' }}>
                暂无导航数据
              </div>
            ) : (
              filteredRootIds.map(id => {
                const node = nodes.get(id);
                if (!node) return null;
                return (
                  <NavTreeNode
                    key={id}
                    node={node}
                    depth={0}
                    isExpanded={expanded.has(id)}
                    isSelected={selectedId === id}
                    isLoading={(node.navId ?? node.id) === loadingId}
                    expandedSet={expanded}
                    loadingId={loadingId}
                    onToggle={toggleNode}
                    onSelect={handleSelect}
                    getChildren={getChildren}
                  />
                );
              })
            )}
          </div>

          {/* Graphic panel / point summary */}
          {selectedNode && (selectedNode.kind === 'equip' || selectedNode.kind === 'site') && (
            <div style={{ borderTop: '1px solid #1e293b' }}>
              <GraphicPanel
                selectedNode={selectedNode}
                graphicUrl={graphicUrl}
                graphicDis={graphicDis}
                graphicLoading={graphicLoading}
                graphicError={graphicError}
                childPoints={childPoints}
              />
            </div>
          )}
        </div>
      )}

      {/* CSS keyframes for spinner */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  );
}
