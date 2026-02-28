// ============================================================
// useNavTree — Lazy-loading tree navigation via Haystack nav op
// ============================================================

import { useState, useCallback, useEffect } from 'react';
import { queryNav } from '../services/haystack';
import type { NavNode } from '../types';
import { Kind, valueIsKind } from 'haystack-core';
import type { HStr, HRef, HNum } from 'haystack-core';

interface TreeState {
  /** All loaded nodes keyed by id */
  nodes: Map<string, NavNode>;
  /** Children ids for each parent (empty string = root) */
  children: Map<string, string[]>;
  /** Expanded node ids */
  expanded: Set<string>;
  /** Currently selected node id */
  selectedId: string | null;
  /** Currently loading parent id */
  loadingId: string | null;
}

function inferKind(row: any): NavNode['kind'] {
  const keys = row.keys as string[];
  if (keys.includes('site')) return 'site';
  if (keys.includes('equip')) return 'equip';
  if (keys.includes('point')) return 'point';
  return 'folder';
}

function parseNavRow(row: any): NavNode {
  const getId = (): string => {
    const id = row.get('id');
    if (id && valueIsKind(id, Kind.Ref)) return (id as HRef).valueOf() as string;
    return String(id ?? '');
  };

  const getStr = (key: string): string | undefined => {
    const val = row.get(key);
    if (val && valueIsKind(val, Kind.Str)) return (val as HStr).valueOf() as string;
    return undefined;
  };

  const getNum = (key: string): number | undefined => {
    const val = row.get(key);
    if (val && valueIsKind(val, Kind.Number)) return (val as HNum).valueOf() as number;
    return undefined;
  };

  const id = getId();
  const dis = getStr('dis') ?? getStr('navName') ?? id;
  const navId = getStr('navId');

  // hasChildren: check for 'nav' marker or infer from kind
  const hasNav = row.get('nav');
  const kind = inferKind(row);
  const hasChildren = (hasNav !== undefined && hasNav !== null) || kind === 'site' || kind === 'equip' || kind === 'folder';

  // Collect tag names
  const tags: string[] = [];
  for (const key of row.keys as string[]) {
    const val = row.get(key);
    if (val && valueIsKind(val, Kind.Marker)) {
      tags.push(key);
    }
  }

  // Current value for points
  const curVal = getNum('curVal') ?? getStr('curVal');
  const unit = getStr('unit');

  // Graphic reference
  const graphicRefVal = row.get('graphicRef');
  const graphicRef = graphicRefVal && valueIsKind(graphicRefVal, Kind.Ref)
    ? (graphicRefVal as HRef).valueOf() as string
    : undefined;

  return { id, dis, navId, hasChildren, kind, tags, curVal, unit, graphicRef };
}

export function useNavTree() {
  const [state, setState] = useState<TreeState>({
    nodes: new Map(),
    children: new Map(),
    expanded: new Set(),
    selectedId: null,
    loadingId: null,
  });

  const loadChildren = useCallback(async (parentNavId?: string) => {
    const parentKey = parentNavId ?? '';
    setState(prev => ({ ...prev, loadingId: parentKey }));

    try {
      const grid = await queryNav(parentNavId);
      if (!grid) {
        setState(prev => ({ ...prev, loadingId: null }));
        return;
      }

      const childNodes: NavNode[] = [];
      for (const row of grid) {
        childNodes.push(parseNavRow(row));
      }

      setState(prev => {
        const nodes = new Map(prev.nodes);
        const children = new Map(prev.children);
        const childIds: string[] = [];

        for (const node of childNodes) {
          nodes.set(node.id, node);
          childIds.push(node.id);
        }
        children.set(parentKey, childIds);

        return { ...prev, nodes, children, loadingId: null };
      });
    } catch (err) {
      console.error('Failed to load nav children:', err);
      setState(prev => ({ ...prev, loadingId: null }));
    }
  }, []);

  const expandNode = useCallback((nodeId: string) => {
    setState(prev => {
      const node = prev.nodes.get(nodeId);
      if (!node) return prev;

      const expanded = new Set(prev.expanded);
      expanded.add(nodeId);

      // Load children if not yet loaded
      const navId = node.navId ?? nodeId;
      if (!prev.children.has(navId)) {
        // Trigger async load
        loadChildren(navId);
      }

      return { ...prev, expanded };
    });
  }, [loadChildren]);

  const collapseNode = useCallback((nodeId: string) => {
    setState(prev => {
      const expanded = new Set(prev.expanded);
      expanded.delete(nodeId);
      return { ...prev, expanded };
    });
  }, []);

  const toggleNode = useCallback((nodeId: string) => {
    setState(prev => {
      if (prev.expanded.has(nodeId)) {
        const expanded = new Set(prev.expanded);
        expanded.delete(nodeId);
        return { ...prev, expanded };
      } else {
        const node = prev.nodes.get(nodeId);
        if (!node) return prev;
        const expanded = new Set(prev.expanded);
        expanded.add(nodeId);
        const navId = node.navId ?? nodeId;
        if (!prev.children.has(navId)) {
          loadChildren(navId);
        }
        return { ...prev, expanded };
      }
    });
  }, [loadChildren]);

  const selectNode = useCallback((nodeId: string) => {
    setState(prev => ({ ...prev, selectedId: nodeId }));
  }, []);

  // Load root nodes on mount
  useEffect(() => {
    loadChildren();
  }, [loadChildren]);

  const rootIds = state.children.get('') ?? [];
  const selectedNode = state.selectedId ? state.nodes.get(state.selectedId) ?? null : null;

  const getChildren = (nodeId: string): NavNode[] => {
    const node = state.nodes.get(nodeId);
    const navId = node?.navId ?? nodeId;
    const ids = state.children.get(navId) ?? [];
    return ids.map(id => state.nodes.get(id)).filter(Boolean) as NavNode[];
  };

  return {
    rootIds,
    nodes: state.nodes,
    expanded: state.expanded,
    selectedId: state.selectedId,
    selectedNode,
    loadingId: state.loadingId,
    getChildren,
    expandNode,
    collapseNode,
    toggleNode,
    selectNode,
    reload: () => loadChildren(),
  };
}
