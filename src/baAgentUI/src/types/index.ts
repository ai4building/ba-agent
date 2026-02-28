// ============================================================
// baAgentUI Type Definitions
// Types for AI Agent interactions with FIN Framework
// ============================================================

// Message types for AI chat
export type MessageType = 'user' | 'assistant' | 'system' | 'error';

export interface ChatMessage {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  // Structured result from AI operations
  result?: AgentResult;
  // Metadata for additional info
  metadata?: Record<string, unknown>;
}

// Agent operation result types
export type AgentAction =
  | 'diagnose'
  | 'optimize'
  | 'inspect'
  | 'hmi'
  | 'report'
  | 'ticket'
  | 'general'
  | 'unknown';

export interface AgentResult {
  action: AgentAction;
  ok: boolean;
  data?: unknown;
  error?: string;
  summary?: string;
}

// Diagnosis types (matching Python FDD engine output)
export type FaultSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type FaultCategory =
  | 'sensor'
  | 'mechanical'
  | 'control'
  | 'capacity'
  | 'energy'
  | 'unknown';

export interface RcaStep {
  point_id: string;
  point_name: string;
  observation: string;
  is_abnormal: boolean;
  value?: number;
  expected_range?: [number, number];
}

export interface DiagnosisData {
  fault_category: FaultCategory;
  root_cause: string;
  explanation: string;
  confidence: number;
  severity: FaultSeverity;
  rca_chain: RcaStep[];
  affected_equipment: string[];
  recommendations: string[];
}

// Optimization types
export interface OptimizationData {
  equip_id: string;
  equip_name: string;
  current_energy: number;
  predicted_savings: number;
  savings_percent: number;
  setpoints: SetpointRecommendation[];
  rationale: string;
}

export interface SetpointRecommendation {
  point_id: string;
  point_name: string;
  current_value: number;
  recommended_value: number;
  unit: string;
  priority: 'high' | 'medium' | 'low';
}

// Inspection types
export interface InspectionData {
  total_sensors: number;
  healthy_count: number;
  warning_count: number;
  failed_count: number;
  sensors: SensorHealth[];
}

export interface SensorHealth {
  point_id: string;
  point_name: string;
  health_score: number;
  status: 'healthy' | 'warning' | 'failed';
  findings: string[];
  last_checked: Date;
}

// HMI generation types
export interface HmiLayout {
  total_pages: number;
  total_widgets: number;
  pages: HmiPage[];
  navigation: HmiNavigation[];
}

export interface HmiPage {
  id: string;
  title: string;
  equip_type: string;
  grid_columns: number;
  grid_rows: number;
  widgets: HmiWidget[];
}

export interface HmiWidget {
  id: string;
  label: string;
  widget_type: 'gauge' | 'trend' | 'status' | 'setpoint' | 'alarm';
  point_id: string;
  row: number;
  col: number;
  row_span: number;
  col_span: number;
}

export interface HmiNavigation {
  id: string;
  label: string;
  target_page: string;
  icon?: string;
}

// API request/response types
export interface AgentRequest {
  action: AgentAction;
  params: Record<string, unknown>;
  context?: {
    user_id?: string;
    session_id?: string;
    timestamp: string;
  };
}

export interface AgentResponse {
  ok: boolean;
  action: AgentAction;
  data?: unknown;
  error?: string;
  _meta?: {
    timestamp: string;
    processing_time_ms: number;
    version: string;
  };
}

// Haystack point reference
export interface HaystackRef {
  id: string;
  dis?: string;
  type: 'point' | 'equip' | 'alarm' | 'site';
}

// Equipment context for diagnosis
export interface EquipmentContext {
  equip_id: string;
  equip_name: string;
  equip_type?: string;
  site_id?: string;
  points: Array<{
    id: string;
    name: string;
    kind: string;
    unit: string;
    cur_val?: unknown;
  }>;
}

// ============================================================
// WebSocket Chat Protocol Types
// ============================================================

export type WsFrameType = 'message' | 'progress' | 'result' | 'error' | 'context';

export interface WsFrame {
  type: WsFrameType;
  id: string;
  timestamp: string;
}

export interface WsMessageFrame extends WsFrame {
  type: 'message';
  content: string;
  context?: ContextSnapshot;
}

export interface WsProgressFrame extends WsFrame {
  type: 'progress';
  percent: number;
  stage: string;
}

export interface WsResultFrame extends WsFrame {
  type: 'result';
  result: AgentResult;
  content: string;
}

export interface WsErrorFrame extends WsFrame {
  type: 'error';
  code: string;
  message: string;
}

export interface ContextSnapshot {
  activeAlarms: number;
  selectedEquipRef?: string;
  currentView: 'chat' | 'hmi' | 'inspection' | 'optimization' | 'context';
  recentPointIds: string[];
}

// Navigation tree types for context browser
export interface NavNode {
  id: string;
  dis: string;
  navId?: string;
  hasChildren: boolean;
  kind: 'site' | 'equip' | 'point' | 'folder';
  tags?: string[];
  curVal?: number | string | boolean;
  unit?: string;
  graphicRef?: string;
}

export type WsConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface StreamingMessage extends ChatMessage {
  isStreaming: boolean;
  fullContent: string;
  displayedContent: string;
}

// ============================================================
// Audit / Approval Types
// ============================================================

export type ApprovalStatus = 'pending' | 'reviewing' | 'approved' | 'rejected' | 'expired';

export interface PendingAiAction {
  id: string;
  pointId: string;
  pointName: string;
  equipName: string;
  currentValue: number;
  suggestedValue: number;
  unit: string;
  rationale: string;
  confidence: number;
  timestamp: Date;
  status: ApprovalStatus;
  isLifeSafety: boolean;
  expiresAt?: Date;
}

export interface AuditLogEntry {
  actionId: string;
  pointId: string;
  operator: string;
  decision: 'approved' | 'rejected';
  timestamp: Date;
  previousValue: number;
  newValue: number;
}

// ============================================================
// SVG Widget Props (HMI Canvas)
// ============================================================

export interface SvgWidgetProps {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  pointId: string;
  currentValue?: number | string | boolean;
  unit?: string;
  onClick?: () => void;
  isSelected?: boolean;
}

// Haystack point data for audit detection
export interface HaystackPointData {
  id: string;
  dis: string;
  equipRef?: string;
  equipDis?: string;
  curVal?: number;
  aiSuggestedVal?: number;
  unit?: string;
  tags: string[];
}
