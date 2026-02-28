// ============================================================
// ContextWatcher — Captures current UI context for AI messages
// ============================================================

import type { ContextSnapshot } from '../types';

interface ContextDeps {
  alarmCount: number;
  selectedEquipRef?: string;
  currentView: string;
  recentPointIds: string[];
}

const VALID_VIEWS = ['chat', 'hmi', 'inspection', 'optimization', 'context'] as const;
type ValidView = (typeof VALID_VIEWS)[number];

function isValidView(v: string): v is ValidView {
  return (VALID_VIEWS as readonly string[]).includes(v);
}

export class ContextWatcher {
  static capture(deps: ContextDeps): ContextSnapshot {
    return {
      activeAlarms: deps.alarmCount,
      selectedEquipRef: deps.selectedEquipRef,
      currentView: isValidView(deps.currentView) ? deps.currentView : 'chat',
      recentPointIds: deps.recentPointIds.slice(0, 20),
    };
  }
}
