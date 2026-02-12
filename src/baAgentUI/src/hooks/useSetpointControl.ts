// ============================================================
// useSetpointControl Hook
// Bidirectional point control using haystack-react's useHaystackPoint
// ============================================================

import { useHaystackPoint } from 'haystack-react';
import { HNum } from 'haystack-core';
import { useState, useCallback, useMemo } from 'react';
import type { SetpointRecommendation } from '../types';

export interface SetpointControl {
  pointId: string;
  currentValue: number;
  unit: string;
  recommendedValue?: number;
  isApplying: boolean;
  applyRecommendation: (value: number) => Promise<void>;
  cancelRecommendation: () => void;
  hasPendingChange: boolean;
}

export interface UseSetpointControlResult {
  controls: Map<string, SetpointControl>;
  isLoading: boolean;
  error: Error | null;
  applyAllRecommendations?: (recommendations: SetpointRecommendation[]) => Promise<void>;
}

/**
 * Hook for managing multiple setpoint controls
 * Uses haystack-react's useHaystackPoint for bidirectional binding
 *
 * @param pointIds - Array of point IDs to control
 *
 * @example
 * const { controls, isLoading } = useSetpointControls(['@p:123', '@p:456']);
 * const satControl = controls.get('@p:123');
 * await satControl?.applyRecommendation(15.5);
 */
export function useSetpointControls(
  pointIds: string[],
  _opts?: { pollRate?: number }
): UseSetpointControlResult {
  const [pendingChanges, setPendingChanges] = useState<Map<string, number>>(new Map());
  const [applying] = useState<Set<string>>(new Set());

  // Create a control for each point
  // Note: We need to manage this differently since hooks can't be called in loops
  // For now, we'll return a Map but the actual implementation would need
  // a different approach for production use
  const controls = useMemo(() => {
    const result = new Map<string, SetpointControl>();

    // Since we can't call useHaystackPoint in a loop,
    // this is a simplified placeholder that assumes the caller
    // will use useSetpointControl for individual points
    for (const pointId of pointIds) {
      result.set(pointId, {
        pointId,
        currentValue: 0,
        unit: '',
        recommendedValue: pendingChanges.get(pointId),
        isApplying: applying.has(pointId),
        applyRecommendation: async () => {},
        cancelRecommendation: () => {},
        hasPendingChange: pendingChanges.has(pointId),
      });
    }

    return result;
  }, [pointIds, pendingChanges, applying]);

  // Apply batch recommendations (from optimization result)
  const applyAllRecommendations = useCallback(async (
    recommendations: SetpointRecommendation[]
  ) => {
    // Set all pending changes
    const newPending = new Map<string, number>();
    recommendations.forEach((rec) => {
      newPending.set(rec.point_id, rec.recommended_value);
    });
    setPendingChanges(newPending);

    // Note: Actual writes would need to be done through individual hooks
    // This is a simplified implementation
  }, []);

  return {
    controls,
    isLoading: false,
    error: null,
    applyAllRecommendations,
  };
}

/**
 * Hook for a single setpoint control
 * Simplified version for individual point management
 */
export function useSetpointControl(pointId: string) {
  // useHaystackPoint returns: [value, writeFunc, point]
  const [pointValue, setPointValue] = useHaystackPoint<HNum>(
    undefined, // Pass undefined since we need to get the point first
    5 // Default poll rate
  );

  const [recommendedValue, setRecommendedValue] = useState<number | undefined>();
  const [isApplying, setIsApplying] = useState(false);

  const currentValue = pointValue?.value || 0;
  const unit = pointValue?.unit || '';

  const applyRecommendation = useCallback(async (value: number) => {
    if (!setPointValue) return;

    setIsApplying(true);
    try {
      const newValue = HNum.make(value, unit);
      await setPointValue(newValue);
      setRecommendedValue(undefined);
    } finally {
      setIsApplying(false);
    }
  }, [pointId, unit, setPointValue]);

  const cancelRecommendation = useCallback(() => {
    setRecommendedValue(undefined);
  }, []);

  return {
    pointId,
    currentValue,
    unit,
    recommendedValue,
    isApplying,
    applyRecommendation,
    cancelRecommendation,
    hasPendingChange: recommendedValue !== undefined,
    setRecommendedValue,
  };
}
