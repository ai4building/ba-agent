export { useHaystackAgent } from './useHaystackAgent';
export { useAlarmWatch, useAlarmById } from './useAlarmWatch';
export { useSetpointControl, useSetpointControls } from './useSetpointControl';
export {
  useEquipmentContext,
  useEquipmentById,
  useEquipmentByType,
} from './useEquipmentContext';
export { useChatAgent } from './useChatAgent';
export { useAgentChat } from './useAgentChat';
export { useAuditActions } from './useAuditActions';

// Re-export utility functions for convenience
export { formatTemperature, formatPower, formatPressure, formatFlow } from '../utils/unitConversion';
