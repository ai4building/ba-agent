// ============================================================
// useChatAgent Hook
// Manages AI chat state and API communication
// ============================================================

import { useState, useCallback } from 'react';
import { getHaystackClient } from '../api/haystack';
import type { ChatMessage, AgentResult } from '../types';

interface UseChatAgentResult {
  messages: ChatMessage[];
  sendMessage: (text: string) => Promise<void>;
  isLoading: boolean;
}

export function useChatAgent(): UseChatAgentResult {
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
      // Parse user intent and route to appropriate operation
      const intent = parseIntent(text);
      let result: AgentResult | null = null;

      const client = getHaystackClient();

      switch (intent.action) {
        case 'diagnose':
          result = await handleDiagnosis(client, text);
          break;
        case 'optimize':
          result = await handleOptimization(client, text);
          break;
        case 'inspect':
          result = await handleInspection(client, text);
          break;
        case 'hmi':
          result = await handleHmiGeneration(client, text);
          break;
        default:
          // General chat - send to AI agent
          result = await handleGeneralChat(client, text);
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

// Operation handlers
async function handleDiagnosis(client: Awaited<ReturnType<typeof getHaystackClient>>, text: string): Promise<AgentResult> {
  // Try to extract alarm ID or filter from text
  const alarmMatch = text.match(/@?([a-zA-Z0-9-]+)/);

  if (alarmMatch) {
    const response = await client.agentDiagnose(alarmMatch[1], { hisRange: 'past1hr' });
    return {
      action: 'diagnose',
      ok: response.ok,
      data: response.data,
      error: response.error,
    };
  }

  // Get active alarms and diagnose the first one
  const alarmsResponse = await client.read('alarm and curVal');
  if (!alarmsResponse.ok || !alarmsResponse.data) {
    return {
      action: 'diagnose',
      ok: false,
      error: 'No active alarms found',
    };
  }

  return {
    action: 'diagnose',
    ok: true,
    summary: 'Found active alarms. Would you like me to analyze a specific alarm?',
  };
}

async function handleOptimization(client: Awaited<ReturnType<typeof getHaystackClient>>, text: string): Promise<AgentResult> {
  // Try to extract equipment ID or type from text
  const equipMatch = text.match(/equip[ment]?:?\s*([a-zA-Z0-9-]+)/i);

  if (equipMatch) {
    const response = await client.agentOptimizeSetpoints(equipMatch[1], { target: 'balanced' });
    return {
      action: 'optimize',
      ok: response.ok,
      data: response.data,
      error: response.error,
    };
  }

  // Get all equipment for optimization
  void await client.read('equip');
  return {
    action: 'optimize',
    ok: true,
    summary: 'I can help optimize setpoints. Please specify which equipment or type (e.g., "optimize AHU-1")',
  };
}

async function handleInspection(client: Awaited<ReturnType<typeof getHaystackClient>>, text: string): Promise<AgentResult> {
  // Determine filter from text
  let filter = 'sensor';

  if (text.toLowerCase().includes('temp')) {
    filter = 'temp and sensor';
  } else if (text.toLowerCase().includes('ahu')) {
    filter = 'sensor and equipRef->equip==ahu';
  }

  const response = await client.agentInspect(filter, { hisRange: 'pastWeek' });

  return {
    action: 'inspect',
    ok: response.ok,
    data: response.data,
    error: response.error,
  };
}

async function handleHmiGeneration(client: Awaited<ReturnType<typeof getHaystackClient>>, text: string): Promise<AgentResult> {
  // Extract equipment type filter from text
  let filter = 'equip';

  if (text.toLowerCase().includes('ahu')) {
    filter = 'ahu';
  } else if (text.toLowerCase().includes('vav')) {
    filter = 'vav';
  } else if (text.toLowerCase().includes('chiller')) {
    filter = 'chiller';
  }

  const response = await client.agentGenHmiLayout(filter, { gridColumns: 6 });

  return {
    action: 'hmi',
    ok: response.ok,
    data: response.data,
    error: response.error,
  };
}

async function handleGeneralChat(client: Awaited<ReturnType<typeof getHaystackClient>>, text: string): Promise<AgentResult> {
  // For general chat, use the AI agent Op
  try {
    const response = await client.invokeOp('agentAsk', { question: text });
    return {
      action: 'general',
      ok: response.ok,
      data: response.data,
      error: response.error,
    };
  } catch {
    return {
      action: 'general',
      ok: true,
      summary: 'I understand you\'re asking about: "' + text + '"\n\n' +
        'I can help with specific tasks like:\n' +
        '- "Diagnose the alarm on AHU-1"\n' +
        '- "Optimize setpoints for VAV-2"\n' +
        '- "Inspect all temperature sensors"\n' +
        '- "Generate HMI layout for all AHUs"',
    };
  }
}

function generateResponseText(intent: ParsedIntent, result: AgentResult | null): string {
  if (!result) return 'I apologize, but I couldn\'t process that request.';

  if (!result.ok) {
    return `I encountered an error: ${result.error || 'Unknown error'}`;
  }

  if (result.summary) {
    return result.summary;
  }

  // Default responses based on action
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
