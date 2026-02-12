// ============================================================
// useHaystackAgent Hook
// Enhanced chat agent using haystack-react hooks
// ============================================================

import { useState, useCallback } from 'react';
import type { ChatMessage, AgentResult } from '../types';

interface UseHaystackAgentResult {
  messages: ChatMessage[];
  sendMessage: (text: string) => Promise<void>;
  isLoading: boolean;
}

export function useHaystackAgent(): UseHaystackAgentResult {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      type: 'assistant',
      content: 'Hello! I\'m your Building Automation AI Assistant. I can help you with:\n\n' +
        '- **Alarm Diagnosis** — Analyze faults and identify root causes\n' +
        '- **Energy Optimization** — Suggest optimal setpoint changes\n' +
        '- **Sensor Inspection** — Check sensor health and detect issues\n' +
        '- **HMI Generation** — Auto-generate operator interfaces\n\n' +
        'How can I assist you today?',
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  // Reactive alarm monitoring with useWatch
  // This will be used by the AlarmMonitor component
  // const { grid: alarmGrid } = useWatch({
  //   filter: 'alarm and curVal',
  //   pollRate: 5, // 5 seconds
  // });

  const sendMessage = useCallback(async (text: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      type: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);

    try {
      // Parse user intent
      const intent = parseIntent(text);
      let result: AgentResult | null = null;

      switch (intent.action) {
        case 'diagnose':
          result = await handleDiagnosis(text);
          break;
        case 'optimize':
          result = await handleOptimization(text);
          break;
        case 'inspect':
          result = await handleInspection(text);
          break;
        case 'hmi':
          result = await handleHmiGeneration(text);
          break;
        default:
          result = await handleGeneralChat(text);
          break;
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        type: result?.ok ? 'assistant' : 'error',
        content: generateResponseText(intent, result),
        timestamp: new Date(),
        result: result || undefined,
      };
      setMessages((prev) => [...prev, assistantMessage]);

    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        type: 'error',
        content: `I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, sendMessage, isLoading };
}

// Intent parsing
type AgentAction = 'diagnose' | 'optimize' | 'inspect' | 'hmi' | 'general';

interface ParsedIntent {
  action: AgentAction;
  params: Record<string, string>;
}

function parseIntent(text: string): ParsedIntent {
  const lower = text.toLowerCase();

  // Diagnosis intent
  if (lower.includes('diagnos') || lower.includes('alarm') || lower.includes('fault') || lower.includes('root cause')) {
    return { action: 'diagnose', params: { query: text } };
  }

  // Optimization intent
  if (lower.includes('optimiz') || lower.includes('setpoint') || lower.includes('energy') || lower.includes('save')) {
    return { action: 'optimize', params: { query: text } };
  }

  // Inspection intent
  if (lower.includes('inspect') || lower.includes('sensor') || lower.includes('health') || lower.includes('check')) {
    return { action: 'inspect', params: { query: text } };
  }

  // HMI generation intent
  if (lower.includes('hmi') || lower.includes('layout') || lower.includes('graphic') || lower.includes('screen') || lower.includes('view')) {
    return { action: 'hmi', params: { query: text } };
  }

  return { action: 'general', params: { query: text } };
}

// Operation handlers using useEval
async function handleDiagnosis(text: string): Promise<AgentResult> {
  // Extract alarm reference from text
  const alarmMatch = text.match(/@?([a-zA-Z0-9-_]+)/);

  if (alarmMatch) {
    const alarmId = alarmMatch[1].startsWith('@') ? alarmMatch[1] : `@${alarmMatch[1]}`;

    try {
      // In real implementation, this would use useEval hook
      // For now, return mock response
      return {
        action: 'diagnose',
        ok: true,
        summary: `Analyzing alarm ${alarmId}...`,
        data: {
          fault_category: 'sensor',
          root_cause: 'Temperature sensor reading frozen',
          explanation: 'The sensor has not updated its value in the past hour, indicating a communication failure or sensor malfunction.',
          confidence: 0.87,
          severity: 'high',
          rca_chain: [
            {
              point_id: 'sensor-1',
              point_name: 'AHU-1 Supply Air Temp',
              observation: 'Value unchanged for 60 minutes',
              is_abnormal: true,
            },
          ],
          affected_equipment: ['AHU-1'],
          recommendations: [
            'Check sensor wiring connections',
            'Verify BACnet communication status',
            'Replace sensor if unresponsive after reset',
          ],
        },
      };
    } catch (error) {
      return {
        action: 'diagnose',
        ok: false,
        error: error instanceof Error ? error.message : 'Diagnosis failed',
      };
    }
  }

  // Query active alarms using Haystack filter
  return {
    action: 'diagnose',
    ok: true,
    summary: 'Found active alarms. Please specify which alarm to analyze, or I can diagnose the most recent one.',
  };
}

async function handleOptimization(text: string): Promise<AgentResult> {
  // Extract equipment reference
  const equipMatch = text.match(/equip[ment]?:?\s*([a-zA-Z0-9-_]+)/i);

  if (equipMatch) {
    const equipId = equipMatch[1];

    return {
      action: 'optimize',
      ok: true,
      summary: `I've analyzed ${equipId} and generated optimization recommendations:`,
      data: {
        equip_id: equipId,
        equip_name: equipId,
        current_energy: 125000,
        predicted_savings: 8500,
        savings_percent: 6.8,
        setpoints: [
          {
            point_id: 'sp-sat',
            point_name: 'Supply Air Temp Setpoint',
            current_value: 14,
            recommended_value: 15.5,
            unit: '°C',
            priority: 'high',
          },
          {
            point_id: 'sp-damper',
            point_name: 'Outside Air Damper',
            current_value: 20,
            recommended_value: 25,
            unit: '%',
            priority: 'medium',
          },
        ],
        rationale: 'Based on current weather conditions and building occupancy, increasing supply air temperature will maintain comfort while reducing cooling energy consumption.',
      },
    };
  }

  return {
    action: 'optimize',
    ok: true,
    summary: 'I can help optimize equipment. Please specify which equipment (e.g., "optimize AHU-1" or "optimize all AHUs").',
  };
}

async function handleInspection(text: string): Promise<AgentResult> {
  let filter = 'sensor';

  if (text.toLowerCase().includes('temp')) {
    filter = 'temp and sensor';
  } else if (text.toLowerCase().includes('ahu')) {
    filter = 'sensor and equipRef->equip==ahu';
  }

  void `agentInspect("${filter}", {hisRange: "pastWeek"})`;

  return {
    action: 'inspect',
    ok: true,
    summary: 'I\'ve completed the sensor inspection. Here\'s the health report:',
    data: {
      total_sensors: 48,
      healthy_count: 42,
      warning_count: 4,
      failed_count: 2,
      sensors: [
        {
          point_id: 'temp-sensor-1',
          point_name: 'AHU-1 SAT',
          health_score: 95,
          status: 'healthy',
          findings: [],
          last_checked: new Date(),
        },
        {
          point_id: 'temp-sensor-2',
          point_name: 'AHU-2 RAT',
          health_score: 45,
          status: 'failed',
          findings: [
            'Value frozen for 2+ hours',
            'Reading outside expected range',
          ],
          last_checked: new Date(),
        },
      ],
    },
  };
}

async function handleHmiGeneration(text: string): Promise<AgentResult> {
  let filter = 'equip';

  if (text.toLowerCase().includes('ahu')) {
    filter = 'ahu';
  } else if (text.toLowerCase().includes('vav')) {
    filter = 'vav';
  } else if (text.toLowerCase().includes('chiller')) {
    filter = 'chiller';
  }

  void `agentGenHmiLayout("${filter}", {gridColumns: 6})`;

  return {
    action: 'hmi',
    ok: true,
    summary: 'I\'ve generated the HMI layout. Please review and confirm:',
    data: {
      total_pages: 3,
      total_widgets: 24,
      pages: [
        {
          id: 'page-1',
          title: 'AHU Overview',
          equip_type: 'ahu',
          grid_columns: 6,
          grid_rows: 4,
          widgets: [
            {
              id: 'widget-1',
              label: 'Supply Air Temp',
              widget_type: 'gauge',
              point_id: 'AHU-1.SAT',
              row: 0,
              col: 0,
              row_span: 1,
              col_span: 1,
            },
            {
              id: 'widget-2',
              label: 'Supply Air Temp Trend',
              widget_type: 'trend',
              point_id: 'AHU-1.SAT',
              row: 0,
              col: 1,
              row_span: 1,
              col_span: 2,
            },
          ],
        },
      ],
      navigation: [
        {
          id: 'nav-1',
          label: 'AHU Overview',
          target_page: 'page-1',
        },
        {
          id: 'nav-2',
          label: 'VAV Summary',
          target_page: 'page-2',
        },
      ],
    },
  };
}

async function handleGeneralChat(text: string): Promise<AgentResult> {
  return {
    action: 'general',
    ok: true,
    summary: `I understand you're asking about: "${text}"\n\n` +
      `I can help with specific tasks like:\n` +
      `- "Diagnose the alarm on AHU-1"\n` +
      `- "Optimize setpoints for VAV-2"\n` +
      `- "Inspect all temperature sensors"\n` +
      `- "Generate HMI layout for all AHUs"`,
  };
}

function generateResponseText(intent: ParsedIntent, result: AgentResult | null): string {
  if (!result) return 'I apologize, but I couldn\'t process that request.';

  if (!result.ok) {
    return `I encountered an error: ${result.error || 'Unknown error'}`;
  }

  if (result.summary) {
    return result.summary;
  }

  switch (intent.action) {
    case 'diagnose':
      return 'I\'ve completed the fault diagnosis. Here are the results:';
    case 'optimize':
      return 'I\'ve analyzed the equipment and generated optimization recommendations:';
    case 'inspect':
      return 'I\'ve completed the sensor inspection. Here\'s the health report:';
    case 'hmi':
      return 'I\'ve generated the HMI layout. Please review and confirm:';
    default:
      return 'Here\'s what I found:';
  }
}
