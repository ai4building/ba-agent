// ============================================================
// FIN Haystack API Client
// Handles communication with FIN Framework / Haxall backend
// ============================================================

import type { AgentResponse } from '../types';

export interface HaystackClientConfig {
  baseUrl: string;
  project?: string;
  username?: string;
  password?: string;
  apiKey?: string;
}

export class HaystackClient {
  private config: HaystackClientConfig;
  private authToken: string | null = null;

  constructor(config: HaystackClientConfig) {
    this.config = {
      ...config,
      baseUrl: config.baseUrl.replace(/\/$/, ''), // Remove trailing slash
    };
  }

  // Get authorization header
  private getAuthHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    } else if (this.config.username && this.config.password) {
      // Basic auth for development
      const encoded = btoa(`${this.config.username}:${this.config.password}`);
      headers['Authorization'] = `Basic ${encoded}`;
    } else if (this.config.apiKey) {
      headers['X-Haystack-API-Key'] = this.config.apiKey;
    }

    return headers;
  }

  // Generic fetch wrapper
  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(
        `HTTP ${response.status}: ${error || response.statusText}`
      );
    }

    return response.json() as Promise<T>;
  }

  // Evaluate AXON expression on server
  async eval(expr: string): Promise<AgentResponse> {
    return this.fetch<AgentResponse>('/api/haystack/eval', {
      method: 'POST',
      body: JSON.stringify({ expr }),
    });
  }

  // Read records by filter
  async read(filter: string): Promise<AgentResponse> {
    return this.fetch<AgentResponse>('/api/haystack/read', {
      method: 'POST',
      body: JSON.stringify({ filter }),
    });
  }

  // Read records by IDs
  async readByIds(ids: string[]): Promise<AgentResponse> {
    return this.fetch<AgentResponse>('/api/haystack/readByIds', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    });
  }

  // Invoke custom Agent operation
  async invokeOp(
    opName: string,
    params: Record<string, unknown> = {}
  ): Promise<AgentResponse> {
    return this.fetch<AgentResponse>(`/api/${opName}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Agent-specific operations
  async agentDiagnose(
    alarmRef: string,
    opts?: { hisRange?: string; message?: string }
  ): Promise<AgentResponse> {
    const params: Record<string, unknown> = { alarmRef };
    if (opts?.hisRange) params.hisRange = opts.hisRange;
    if (opts?.message) params.message = opts.message;
    return this.invokeOp('agentDiagnose', params);
  }

  async agentOptimizeSetpoints(
    equipRef: string,
    opts?: { target?: string; hisRange?: string }
  ): Promise<AgentResponse> {
    const params: Record<string, unknown> = { equipRef };
    if (opts?.target) params.target = opts.target;
    if (opts?.hisRange) params.hisRange = opts.hisRange;
    return this.invokeOp('agentOptimizeSetpoints', params);
  }

  async agentInspect(
    filter: string,
    opts?: { hisRange?: string }
  ): Promise<AgentResponse> {
    const params: Record<string, unknown> = { filter };
    if (opts?.hisRange) params.hisRange = opts.hisRange;
    return this.invokeOp('agentInspect', params);
  }

  async agentGenHmiLayout(
    filter: string,
    opts?: { gridColumns?: number }
  ): Promise<AgentResponse> {
    const params: Record<string, unknown> = { filter };
    if (opts?.gridColumns) params.gridColumns = opts.gridColumns;
    return this.invokeOp('agentGenHmiLayout', params);
  }

  async agentPreviewHmi(layoutResult: unknown): Promise<AgentResponse> {
    return this.invokeOp('agentPreviewHmi', { layoutResult });
  }

  async agentTicketGen(diagnosis: unknown): Promise<AgentResponse> {
    return this.invokeOp('agentTicketGen', { diagnosis });
  }

  async agentLoadShed(opts?: {
    level?: number;
    duration?: string;
    equipFilter?: string;
  }): Promise<AgentResponse> {
    return this.invokeOp('agentLoadShed', opts || {});
  }

  // Watch/subscribe to point changes (WebSocket would be used here)
  async watchSubscribe(
    filter: string,
    callback: (data: unknown) => void
  ): Promise<() => void> {
    // For polling-based implementation
    // TODO: Implement WebSocket for real-time updates
    const intervalId = setInterval(async () => {
      try {
        const result = await this.read(filter);
        if (result.ok && result.data) {
          callback(result.data);
        }
      } catch (error) {
        console.error('Watch subscription error:', error);
      }
    }, 2000); // 2 second polling

    return () => clearInterval(intervalId);
  }

  // Write point value (with priority for shadow mode)
  async writePoint(
    pointId: string,
    value: unknown,
    level: number = 16 // Priority 16 = Shadow mode (requires confirmation)
  ): Promise<AgentResponse> {
    return this.fetch<AgentResponse>('/api/haystack/write', {
      method: 'POST',
      body: JSON.stringify({
        id: pointId,
        val: value,
        level: { val: level, type: 'Number' },
      }),
    });
  }

  // Confirm pending write (from shadow mode)
  async confirmWrite(pointId: string): Promise<AgentResponse> {
    return this.invokeOp('confirmWrite', { pointId });
  }

  // Cancel pending write
  async cancelWrite(pointId: string): Promise<AgentResponse> {
    return this.invokeOp('cancelWrite', { pointId });
  }
}

// Create singleton instance
let clientInstance: HaystackClient | null = null;

export function getHaystackClient(config?: HaystackClientConfig): HaystackClient {
  if (!clientInstance) {
    if (!config) {
      // Default configuration for development
      config = {
        baseUrl: import.meta.env.VITE_HAYSTACK_API_URL || '/api',
        project: import.meta.env.VITE_HAYSTACK_PROJECT || 'baAgent',
      };
    }
    clientInstance = new HaystackClient(config);
  }
  return clientInstance;
}
