// ============================================================
// NavTreeNode — Single node in the navigation tree
// ============================================================

import { ChevronRight, ChevronDown, Building2, Cpu, CircleDot, Folder, Loader2 } from 'lucide-react';
import type { NavNode } from '../../types';

interface NavTreeNodeProps {
  node: NavNode;
  depth: number;
  isExpanded: boolean;
  isSelected: boolean;
  isLoading: boolean;
  children?: NavNode[];
  expandedSet: Set<string>;
  loadingId: string | null;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  getChildren: (id: string) => NavNode[];
}

const kindIcons: Record<NavNode['kind'], typeof Building2> = {
  site: Building2,
  equip: Cpu,
  point: CircleDot,
  folder: Folder,
};

const kindColors: Record<NavNode['kind'], string> = {
  site: '#60a5fa',
  equip: '#34d399',
  point: '#fbbf24',
  folder: '#94a3b8',
};

export function NavTreeNode({
  node,
  depth,
  isExpanded,
  isSelected,
  isLoading,
  expandedSet,
  loadingId,
  onToggle,
  onSelect,
  getChildren,
}: NavTreeNodeProps) {
  const Icon = kindIcons[node.kind];
  const color = kindColors[node.kind];
  const childNodes = isExpanded ? getChildren(node.id) : [];

  return (
    <div>
      <div
        onClick={() => onSelect(node.id)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 8px',
          paddingLeft: `${8 + depth * 16}px`,
          cursor: 'pointer',
          borderRadius: '6px',
          backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
          borderLeft: isSelected ? '2px solid #3b82f6' : '2px solid transparent',
          transition: 'background-color 0.15s',
          minHeight: '28px',
        }}
        onMouseEnter={e => {
          if (!isSelected) (e.currentTarget as HTMLDivElement).style.backgroundColor = 'rgba(255,255,255,0.05)';
        }}
        onMouseLeave={e => {
          if (!isSelected) (e.currentTarget as HTMLDivElement).style.backgroundColor = 'transparent';
        }}
      >
        {/* Expand/collapse arrow */}
        {node.hasChildren ? (
          <button
            onClick={e => { e.stopPropagation(); onToggle(node.id); }}
            style={{
              background: 'none', border: 'none', padding: '2px', cursor: 'pointer',
              color: '#64748b', display: 'flex', alignItems: 'center', flexShrink: 0,
            }}
          >
            {isLoading ? (
              <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
            ) : isExpanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )}
          </button>
        ) : (
          <span style={{ width: '16px', flexShrink: 0 }} />
        )}

        {/* Kind icon */}
        <Icon size={13} style={{ color, flexShrink: 0 }} />

        {/* Label */}
        <span style={{
          fontSize: '12px',
          color: isSelected ? '#e2e8f0' : '#cbd5e1',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          flex: 1,
        }}>
          {node.dis}
        </span>

        {/* Point current value */}
        {node.kind === 'point' && node.curVal !== undefined && (
          <span style={{
            fontSize: '10px',
            color: '#94a3b8',
            fontFamily: 'monospace',
            flexShrink: 0,
          }}>
            {typeof node.curVal === 'boolean' ? (node.curVal ? 'ON' : 'OFF') : node.curVal}
            {node.unit ? ` ${node.unit}` : ''}
          </span>
        )}
      </div>

      {/* Recursive children */}
      {isExpanded && childNodes.length > 0 && (
        <div>
          {childNodes.map(child => (
            <NavTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              isExpanded={expandedSet.has(child.id)}
              isSelected={false}
              isLoading={(child.navId ?? child.id) === loadingId}
              expandedSet={expandedSet}
              loadingId={loadingId}
              onToggle={onToggle}
              onSelect={onSelect}
              getChildren={getChildren}
            />
          ))}
        </div>
      )}
    </div>
  );
}
