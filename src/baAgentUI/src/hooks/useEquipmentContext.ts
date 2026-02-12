// ============================================================
// useEquipmentContext Hook
// Equipment and point queries using haystack-react's useReadByFilter
// ============================================================

import { useReadByFilter } from 'haystack-react';
import { HRef, HStr, HNum } from 'haystack-core';
import { useMemo } from 'react';

export interface PointInfo {
  id: string;
  dis: string;
  kind: string;
  unit: string;
  curVal?: number;
  curStatus?: string;
}

export interface EquipmentInfo {
  id: string;
  dis: string;
  equipType?: string;
  siteRef?: string;
  pointCount: number;
  points: PointInfo[];
}

/**
 * Hook for querying equipment and their points
 * Uses haystack-react's useReadByFilter for efficient queries
 *
 * @param filter - Haystack filter expression (e.g., "ahu", "equip and siteRef==@site-1")
 *
 * @example
 * const { equipment, isLoading, error } = useEquipmentContext('ahu');
 */
export function useEquipmentContext(filter: string) {
  // Read equipment and all their points in a single query
  const { grid, isLoading, error } = useReadByFilter(
    `equip or point and equipRef->${filter}`
  );

  const equipment = useMemo(() => {
    if (!grid) return [];

    const equipMap = new Map<string, EquipmentInfo>();

    // HGrid is iterable, returning HDict for each row
    for (const dict of grid) {
      const idVal = dict.get('id');
      const id = idVal instanceof HRef ? idVal.value : '';
      const isEquip = dict.has('equip');
      const isPoint = dict.has('point');

      if (isEquip) {
        const equipTypeVal = dict.get('equip');
        const equipType = equipTypeVal instanceof HStr ? equipTypeVal.value : undefined;

        const disVal = dict.get('dis');
        const dis = disVal instanceof HStr ? disVal.value : id;

        const siteRefVal = dict.get('siteRef');
        const siteRef = siteRefVal instanceof HRef ? siteRefVal.value : undefined;

        equipMap.set(id, {
          id,
          dis,
          equipType,
          siteRef,
          pointCount: 0,
          points: [],
        });
      } else if (isPoint) {
        const equipRefVal = dict.get('equipRef');
        const equipId = equipRefVal instanceof HRef ? equipRefVal.value : '';

        if (equipId && equipMap.has(equipId)) {
          const equip = equipMap.get(equipId)!;

          const disVal = dict.get('dis');
          const kindVal = dict.get('kind');
          const unitVal = dict.get('unit');
          const curVal = dict.get('curVal');

          const pointInfo: PointInfo = {
            id,
            dis: disVal instanceof HStr ? disVal.value : id,
            kind: kindVal instanceof HStr ? kindVal.value : '',
            unit: unitVal instanceof HStr ? unitVal.value : '',
          };

          // Get current value if available
          if (curVal instanceof HNum) {
            pointInfo.curVal = curVal.value;
          }

          equip.points.push(pointInfo);
          equip.pointCount++;
        }
      }
    }

    return Array.from(equipMap.values());
  }, [grid]);

  // Get all points across all equipment
  const allPoints = useMemo(() => {
    return equipment.flatMap((eq) => eq.points);
  }, [equipment]);

  return {
    equipment,
    allPoints,
    totalPoints: allPoints.length,
    isLoading,
    error,
  };
}

/**
 * Hook for getting a specific equipment's context
 *
 * @param equipId - Equipment reference ID
 */
export function useEquipmentById(equipId: string) {
  const { grid, isLoading, error } = useReadByFilter(
    `equip and id==${equipId} or point and equipRef==${equipId}`
  );

  const equipment = useMemo(() => {
    if (!grid) return null;

    const equipInfo: EquipmentInfo = {
      id: equipId,
      dis: '',
      pointCount: 0,
      points: [],
    };

    for (const dict of grid) {
      const isEquip = dict.has('equip');
      const isPoint = dict.has('point');

      const disVal = dict.get('dis');
      const dis = disVal instanceof HStr ? disVal.value : '';

      if (isEquip) {
        equipInfo.dis = dis;
        const equipTypeVal = dict.get('equip');
        equipInfo.equipType = equipTypeVal instanceof HStr ? equipTypeVal.value : undefined;
      } else if (isPoint) {
        const kindVal = dict.get('kind');
        const unitVal = dict.get('unit');

        equipInfo.points.push({
          id: equipId,
          dis: dis,
          kind: kindVal instanceof HStr ? kindVal.value : '',
          unit: unitVal instanceof HStr ? unitVal.value : '',
        });
        equipInfo.pointCount++;
      }
    }

    return equipInfo;
  }, [grid, equipId]);

  return { equipment, isLoading, error };
}

/**
 * Hook for finding equipment by type
 *
 * @param equipType - Equipment type (e.g., "ahu", "vav", "chiller")
 */
export function useEquipmentByType(equipType: string) {
  return useEquipmentContext(equipType);
}
