// ============================================================
// useGraphicViewer — Find and build URL for equipment graphics
// ============================================================

import { useState, useEffect } from 'react';
import { readEntities } from '../services/haystack';
import { Kind, valueIsKind } from 'haystack-core';
import type { HRef, HStr } from 'haystack-core';

const HAYSTACK_PROJECT = import.meta.env.VITE_HAYSTACK_PROJECT || 'demo';

interface GraphicViewerState {
  graphicUrl: string | null;
  graphicId: string | null;
  graphicDis: string | null;
  loading: boolean;
  error: string | null;
}

export function useGraphicViewer(equipId: string | null) {
  const [state, setState] = useState<GraphicViewerState>({
    graphicUrl: null,
    graphicId: null,
    graphicDis: null,
    loading: false,
    error: null,
  });

  useEffect(() => {
    if (!equipId) {
      setState({ graphicUrl: null, graphicId: null, graphicDis: null, loading: false, error: null });
      return;
    }

    let cancelled = false;

    async function fetchGraphic() {
      setState(prev => ({ ...prev, loading: true, error: null }));

      try {
        // Query for graphics associated with this equipment
        const grid = await readEntities(`graphic and equipRef==@${equipId}`);

        if (cancelled) return;

        if (!grid || [...grid].length === 0) {
          setState({ graphicUrl: null, graphicId: null, graphicDis: null, loading: false, error: null });
          return;
        }

        const row = grid.get(0);
        if (!row) {
          setState({ graphicUrl: null, graphicId: null, graphicDis: null, loading: false, error: null });
          return;
        }

        const idVal = row.get('id');
        const graphicId = idVal && valueIsKind(idVal, Kind.Ref)
          ? (idVal as HRef).valueOf() as string
          : null;

        const disVal = row.get('dis');
        const graphicDis = disVal && valueIsKind(disVal, Kind.Str)
          ? (disVal as HStr).valueOf() as string
          : null;

        const graphicUrl = graphicId
          ? `/ui/${HAYSTACK_PROJECT}/graphic/${graphicId}`
          : null;

        setState({ graphicUrl, graphicId, graphicDis, loading: false, error: null });
      } catch (err) {
        if (cancelled) return;
        setState({
          graphicUrl: null,
          graphicId: null,
          graphicDis: null,
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load graphic',
        });
      }
    }

    fetchGraphic();
    return () => { cancelled = true; };
  }, [equipId]);

  return state;
}
