// ============================================================
// useAuditActions — React hook for AI write approval workflow
// ============================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { AuditActionController } from '../core/AuditActionController';
import { getHaystackClient } from '../api/haystack';
import type { PendingAiAction, AuditLogEntry, HaystackPointData } from '../types';

const POLL_INTERVAL = 5000;
const EXPIRE_CHECK_INTERVAL = 60000;

export function useAuditActions() {
  const controllerRef = useRef<AuditActionController>(new AuditActionController());
  const [pendingActions, setPendingActions] = useState<PendingAiAction[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [reviewingAction, setReviewingAction] = useState<PendingAiAction | null>(null);

  const controller = controllerRef.current;
  const client = getHaystackClient();

  // Subscribe to controller changes
  useEffect(() => {
    const unsub = controller.subscribe((actions) => {
      setPendingActions(actions);
      setAuditLog(controller.getAuditLog());
      // Update reviewing action if it was resolved
      setReviewingAction((prev) => {
        if (!prev) return null;
        const found = actions.find((a) => a.id === prev.id);
        return found?.status === 'reviewing' ? found : null;
      });
    });
    return unsub;
  }, [controller]);

  // Poll for AI suggested values
  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const result = await client.read('point and aiSuggestedVal');
        if (!active || !result.ok || !result.data) return;

        const points = result.data as HaystackPointData[];
        controller.detectPendingActions(points);
      } catch {
        // Silently ignore polling errors
      }
    };

    poll();
    const intervalId = setInterval(poll, POLL_INTERVAL);
    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [client, controller]);

  // Periodic expiry check
  useEffect(() => {
    const intervalId = setInterval(() => {
      controller.expireStale();
    }, EXPIRE_CHECK_INTERVAL);
    return () => clearInterval(intervalId);
  }, [controller]);

  const startReview = useCallback(
    (actionId: string) => {
      controller.startReview(actionId);
      const action = controller.getPendingActions().find((a) => a.id === actionId);
      setReviewingAction(action ?? null);
    },
    [controller]
  );

  const approve = useCallback(
    async (actionId: string) => {
      await controller.approve(
        actionId,
        async (pointId) => {
          await client.commitAiChange(pointId);
        }
      );
    },
    [controller, client]
  );

  const reject = useCallback(
    async (actionId: string, reason?: string) => {
      await controller.reject(
        actionId,
        async (pointId) => {
          await client.cancelWrite(pointId);
        },
        'operator',
        reason
      );
    },
    [controller, client]
  );

  return {
    pendingActions,
    reviewingAction,
    auditLog,
    pendingCount: pendingActions.length,
    approve,
    reject,
    startReview,
  };
}
