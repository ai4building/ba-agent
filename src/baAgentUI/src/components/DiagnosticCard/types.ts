/**
 * Types matching the Python FDD engine's DiagnosisResult output.
 * These mirror baAgentPy/services/fdd_engine.py data models.
 */

export type FaultSeverity = "critical" | "high" | "medium" | "low" | "info";

export type FaultCategory =
  | "sensor"
  | "mechanical"
  | "control"
  | "capacity"
  | "energy"
  | "unknown";

export interface RcaStep {
  point_id: string;
  point_name: string;
  observation: string;
  is_abnormal: boolean;
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

export interface DiagnosticResponse {
  ok: boolean;
  action: string;
  r_status: string;
  r_confidence?: number;
  r_message?: string;
  r_data?: string;
  error?: string;
}
