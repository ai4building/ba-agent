// ============================================================
// AuditActionController — Audit state machine for AI write approvals
// Manages pending AI actions, approval flow, and safety barriers
// ============================================================

import type {
  PendingAiAction,
  AuditLogEntry,
  HaystackPointData,
} from '../types';

type AuditEventCallback = (actions: PendingAiAction[]) => void;

const LIFE_SAFETY_TAGS = [
  'fire', 'smoke', 'sprinkler', 'emergencyPower',
  'fireAlarm', 'smokeDetector', 'emergencyShutdown',
  'fireSuppression', 'emergencyExhaust',
];

export class AuditActionController {
  private actions: Map<string, PendingAiAction> = new Map();
  private auditLog: AuditLogEntry[] = [];
  private listeners: Set<AuditEventCallback> = new Set();
  private defaultExpireMs: number;

  constructor(defaultExpireMs: number = 30 * 60 * 1000) {
    this.defaultExpireMs = defaultExpireMs;
  }

  // --- Event subscription ---

  subscribe(callback: AuditEventCallback): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notify(): void {
    const actions = this.getPendingActions();
    for (const cb of this.listeners) {
      cb(actions);
    }
  }

  // --- Detect new AI suggestions from point data ---

  detectPendingActions(points: HaystackPointData[]): PendingAiAction[] {
    const newActions: PendingAiAction[] = [];

    for (const pt of points) {
      if (pt.aiSuggestedVal == null || pt.curVal == null) continue;
      if (this.actions.has(pt.id)) continue;

      const action: PendingAiAction = {
        id: `action-${pt.id}-${Date.now()}`,
        pointId: pt.id,
        pointName: pt.dis,
        equipName: pt.equipDis ?? 'Unknown Equipment',
        currentValue: pt.curVal,
        suggestedValue: pt.aiSuggestedVal,
        unit: pt.unit ?? '',
        rationale: '',
        confidence: 0.8,
        timestamp: new Date(),
        status: 'pending',
        isLifeSafety: this.isLifeSafety(pt.id, pt.tags),
        expiresAt: new Date(Date.now() + this.defaultExpireMs),
      };

      this.actions.set(pt.id, action);
      newActions.push(action);
    }

    if (newActions.length > 0) {
      this.notify();
    }
    return newActions;
  }

  // --- State transitions ---

  startReview(actionId: string): void {
    const action = this.findById(actionId);
    if (!action || action.status !== 'pending') return;
    action.status = 'reviewing';
    this.notify();
  }

  async approve(
    actionId: string,
    commitFn: (pointId: string) => Promise<void>,
    operator: string = 'operator'
  ): Promise<void> {
    const action = this.findById(actionId);
    if (!action) throw new Error(`Action ${actionId} not found`);
    if (action.isLifeSafety) throw new Error('Cannot approve life-safety point');
    if (action.status !== 'reviewing') throw new Error(`Invalid status: ${action.status}`);

    await commitFn(action.pointId);
    action.status = 'approved';

    this.auditLog.push({
      actionId: action.id,
      pointId: action.pointId,
      operator,
      decision: 'approved',
      timestamp: new Date(),
      previousValue: action.currentValue,
      newValue: action.suggestedValue,
    });

    this.notify();
  }

  async reject(
    actionId: string,
    cancelFn: (pointId: string) => Promise<void>,
    operator: string = 'operator',
    _reason?: string
  ): Promise<void> {
    const action = this.findById(actionId);
    if (!action) throw new Error(`Action ${actionId} not found`);
    if (action.status !== 'pending' && action.status !== 'reviewing') {
      throw new Error(`Invalid status: ${action.status}`);
    }

    await cancelFn(action.pointId);
    action.status = 'rejected';

    this.auditLog.push({
      actionId: action.id,
      pointId: action.pointId,
      operator,
      decision: 'rejected',
      timestamp: new Date(),
      previousValue: action.currentValue,
      newValue: action.suggestedValue,
    });

    this.notify();
  }

  expireStale(): void {
    const now = Date.now();
    let changed = false;

    for (const action of this.actions.values()) {
      if (
        action.expiresAt &&
        now > action.expiresAt.getTime() &&
        (action.status === 'pending' || action.status === 'reviewing')
      ) {
        action.status = 'expired';
        changed = true;
      }
    }

    if (changed) this.notify();
  }

  // --- Safety barrier ---

  isLifeSafety(_pointId: string, tags: string[]): boolean {
    return tags.some((tag) => LIFE_SAFETY_TAGS.includes(tag));
  }

  // --- Queries ---

  getPendingActions(): PendingAiAction[] {
    return Array.from(this.actions.values()).filter(
      (a) => a.status === 'pending' || a.status === 'reviewing'
    );
  }

  getAllActions(): PendingAiAction[] {
    return Array.from(this.actions.values());
  }

  getAuditLog(): AuditLogEntry[] {
    return [...this.auditLog];
  }

  // --- Helpers ---

  private findById(actionId: string): PendingAiAction | undefined {
    for (const action of this.actions.values()) {
      if (action.id === actionId) return action;
    }
    return undefined;
  }

  clear(): void {
    this.actions.clear();
    this.notify();
  }
}
