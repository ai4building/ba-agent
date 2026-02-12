// ============================================================
// HaystackContext Provider
// Provides haystack-react Client to all components
// ============================================================

import { createContext, useContext, type ReactNode } from 'react';
import { Client } from 'haystack-nclient';

export interface HaystackContextValue {
  client: Client;
  isConnected: boolean;
  project: string;
}

const HaystackContext = createContext<HaystackContextValue | null>(null);

export interface HaystackProviderProps {
  children: ReactNode;
  baseUrl?: string;
  project?: string;
}

export function HaystackProvider({
  children,
  baseUrl = '/api',
  project = 'baAgent',
}: HaystackProviderProps) {
  // Construct base URL for Client
  const base = new URL(baseUrl, window.location.origin);

  // Create haystack-nclient Client instance
  const client = new Client({
    base,
    project,
    // Auth will be handled by FIN's session
  });

  const value: HaystackContextValue = {
    client,
    isConnected: true, // TODO: implement connection check
    project,
  };

  return (
    <HaystackContext.Provider value={value}>
      {children}
    </HaystackContext.Provider>
  );
}

export function useHaystackContext(): HaystackContextValue {
  const context = useContext(HaystackContext);
  if (!context) {
    throw new Error('useHaystackContext must be used within HaystackProvider');
  }
  return context;
}
