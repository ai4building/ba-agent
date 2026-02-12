// ============================================================
// useAlarmWatch Hook
// Real-time alarm monitoring using haystack-react's useWatch
// ============================================================

import { useWatch } from 'haystack-react';
import { HDict, HBool, HNum, HRef } from 'haystack-core';
import { useMemo } from 'react';

export interface AlarmEvent {
  id: string;
  dis: string;
  curVal: boolean;
  timestamp: Date;
  severity: 'critical' | 'warning' | 'info';
  priority: number;
  equipRef?: string;
}

export interface UseAlarmWatchOptions {
  pollRate?: number; // Polling rate in seconds
  filter?: string;   // Custom filter expression
}

/**
 * Hook for monitoring active alarms in real-time
 * Uses haystack-react's useWatch for automatic polling and updates
 *
 * @example
 * const { alarms, isLoading, error, alarmCount } = useAlarmWatch({ pollRate: 5 });
 */
export function useAlarmWatch(options: UseAlarmWatchOptions = {}) {
  const { pollRate = 5, filter = 'alarm and curVal' } = options;

  // useWatch automatically polls and provides reactive updates
  const { grid, isLoading, error } = useWatch({
    filter,
    pollRate,
  });

  // Parse alarm events from Haystack grid
  const alarms = useMemo(() => {
    if (!grid) return [];

    const alarmEvents: AlarmEvent[] = [];

    // HGrid is iterable, returning HDict for each row
    for (const dict of grid) {
      const idVal = dict.get('id');
      const disVal = dict.get('dis');
      const curVal = dict.get('curVal');
      const priority = dict.get('priority');

      const id = idVal instanceof HRef ? idVal.value : '';
      const dis = disVal && typeof disVal === 'object' && 'value' in disVal
        ? (disVal as { value: string }).value
        : '';

      // Only include active alarms
      const isActive = curVal instanceof HBool ? curVal.value : false;
      if (!isActive) continue;

      const priorityVal = priority instanceof HNum ? priority.value : 99;

      const equipRefVal = dict.get('equipRef');
      alarmEvents.push({
        id,
        dis,
        curVal: true,
        timestamp: new Date(),
        severity: parseSeverity(priorityVal),
        priority: priorityVal,
        equipRef: equipRefVal instanceof HRef ? equipRefVal.value : undefined,
      });
    }

    // Sort by priority (lower number = higher priority)
    return alarmEvents.sort((a, b) => a.priority - b.priority);
  }, [grid]);

  const alarmCount = alarms.length;
  const criticalCount = alarms.filter((a) => a.severity === 'critical').length;
  const warningCount = alarms.filter((a) => a.severity === 'warning').length;

  return {
    alarms,
    alarmCount,
    criticalCount,
    warningCount,
    isLoading,
    error,
  };
}

/**
 * Hook for monitoring a specific alarm by ID
 */
export function useAlarmById(alarmId: string) {
  const { grid, isLoading, error } = useWatch({
    filter: `alarm and id==${alarmId}`,
    pollRate: 2, // Faster polling for specific alarm
  });

  const alarm = useMemo(() => {
    if (!grid) return null;

    // Check if grid has any rows
    const gridArray = Array.from(grid);
    if (gridArray.length === 0) return null;

    const firstDict = gridArray[0];
    if (!firstDict) return null;

    const curVal = firstDict.get('curVal');
    const disVal = firstDict.get('dis');
    const dis = disVal && typeof disVal === 'object' && 'value' in disVal
      ? (disVal as { value: string }).value
      : '';

    return {
      id: alarmId,
      dis,
      curVal: curVal instanceof HBool ? curVal.value : false,
      timestamp: new Date(),
      severity: parseSeverity(firstDict) as 'critical' | 'warning' | 'info',
    };
  }, [grid, alarmId]);

  return { alarm, isLoading, error };
}

function parseSeverity(dictOrPriority: HDict | number): 'critical' | 'warning' | 'info' {
  let priorityVal: number;

  if (typeof dictOrPriority === 'number') {
    priorityVal = dictOrPriority;
  } else {
    const priority = dictOrPriority.get('priority');
    priorityVal = priority instanceof HNum ? priority.value : 99;
  }

  if (priorityVal <= 3) return 'critical';
  if (priorityVal <= 7) return 'warning';
  return 'info';
}
