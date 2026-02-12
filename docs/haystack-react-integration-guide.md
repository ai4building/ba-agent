# haystack-react Integration Guide for baAgentUI

> Practical implementation guide for J2 Innovations' TypeScript/React libraries in baAgentUI

## Overview

J2 Innovations provides a complete TypeScript stack for building Haystack-based applications:

```
┌─────────────────────────────────────────────────────────────┐
│  baAgentUI (React SPA)                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  haystack-react (hooks)                            │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  haystack-nclient (network client)         │    │   │
│  │  │  ┌─────────────────────────────────────┐  │    │   │
│  │  │  │  haystack-core (types & codecs)     │  │    │   │
│  │  │  │  - HVal, HDict, HGrid, HRef, etc.  │  │    │   │
│  │  │  │  - HFilter compiler                 │  │    │   │
│  │  │  │  - Zinc/Hayson/Trio codecs          │  │    │   │
│  │  │  └─────────────────────────────────────┘  │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    ↕ (REST/WebSocket)
┌─────────────────────────────────────────────────────────────┐
│  FIN Framework / Haxall (Haystack Server)                   │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
cd src/baAgentUI
npm install haystack-core haystack-units haystack-nclient haystack-react
```

## Part 1: Client Setup

### 1.1 Client Provider Pattern

Create a client provider to share the Haystack client across all components:

```tsx
// src/contexts/HaystackContext.tsx
import { Client } from 'haystack-nclient';
import { createContext, useContext } from 'react';

interface HaystackContextValue {
  client: Client;
  isConnected: boolean;
}

export const HaystackContext = createContext<HaystackContextValue | null>(null);

export function useHaystackClient() {
  const context = useContext(HaystackContext);
  if (!context) {
    throw new Error('useHaystackClient must be used within HaystackProvider');
  }
  return context;
}

interface HaystackProviderProps {
  children: React.ReactNode;
  baseUrl?: string;
  project?: string;
  username?: string;
  password?: string;
}

export function HaystackProvider({
  children,
  baseUrl = '/api',
  project = 'baAgent',
  username,
  password,
}: HaystackProviderProps) {
  const client = new Client({
    base: new URL(baseUrl, window.location.origin),
    project,
    auth: username && password ? { username, password } : undefined,
  });

  const value: HaystackContextValue = {
    client,
    isConnected: true, // TODO: add actual connection check
  };

  return (
    <HaystackContext.Provider value={value}>
      {children}
    </HaystackContext.Provider>
  );
}
```

### 1.2 App Integration

```tsx
// src/App.tsx
import { HaystackProvider } from './contexts/HaystackContext';
import { DiagnosticView } from './views/DiagnosticView';
import { OptimizationView } from './views/OptimizationView';
import { HmiView } from './views/HmiView';

function App() {
  return (
    <HaystackProvider
      baseUrl="/api"
      project="baAgent"
      // username={localStorage.getItem('username') || undefined}
      // password={localStorage.getItem('password') || undefined}
    >
      <div className="app">
        <nav className="mobile-nav">
          {/* Navigation tabs */}
        </nav>
        <main>
          <DiagnosticView />
          <OptimizationView />
          <HmiView />
        </main>
      </div>
    </HaystackProvider>
  );
}

export default App;
```

## Part 2: Core Hooks for baAgentUI

### 2.1 useReadByFilter — Equipment & Point Queries

Query equipment records for AI diagnosis context:

```tsx
// src/hooks/useEquipmentContext.ts
import { useReadByFilter } from 'haystack-react';
import { HDict } from 'haystack-core';

export interface EquipmentContext {
  id: string;
  dis: string;
  equipRef: string;
  pointCount: number;
}

export function useEquipmentContext(equipId: string) {
  // Read equipment and all its child points
  const { grid, isLoading, error } = useReadByFilter(
    `equip and id==${equipId} or point and equipRef==@${equipId}`
  );

  if (isLoading) return { isLoading: true, equipment: null, error: null };
  if (error) return { isLoading: false, equipment: null, error };

  // Parse equipment data
  const equipments = new Map<string, EquipmentContext>();
  const points: HDict[] = [];

  grid?.rows.forEach((row) => {
    const rec = row.toDict();
    const isEquip = rec.has('equip');
    const isPoint = rec.has('point');

    if (isEquip) {
      const id = rec.get('id')?.toStr() || '';
      equipments.set(id, {
        id,
        dis: rec.get('dis')?.toStr() || id,
        equipRef: rec.get('equipRef')?.toStr() || '',
        pointCount: 0,
      });
    } else if (isPoint) {
      points.push(rec);
      const equipRef = rec.get('equipRef')?.toStr();
      if (equipRef && equipments.has(equipRef)) {
        const equip = equipments.get(equipRef)!;
        equip.pointCount++;
      }
    }
  });

  return {
    isLoading: false,
    equipment: Array.from(equipments.values()),
    points,
    error: null,
  };
}
```

### 2.2 useWatch — Real-Time Point Monitoring

Monitor alarm points for live AI diagnosis triggers:

```tsx
// src/hooks/useAlarmWatch.ts
import { useWatch } from 'haystack-react';
import { HGrid, HDict } from 'haystack-core';

export interface AlarmEvent {
  id: string;
  dis: string;
  curVal: boolean;
  timestamp: Date;
  severity: 'critical' | 'warning' | 'info';
}

export function useAlarmWatch(pollRate: number = 5) {
  // Watch all alarm points with current values
  const { grid, isLoading, error } = useWatch({
    filter: 'alarm and curVal',
    pollRate, // seconds
  });

  const alarms: AlarmEvent[] = [];

  if (!isLoading && !error && grid) {
    grid.rows.forEach((row) => {
      const rec = row.toDict();
      const curVal = rec.get('curVal');
      const isAlarmActive = curVal instanceof HBool ? curVal.val : false;

      if (isAlarmActive) {
        alarms.push({
          id: rec.get('id')?.toStr() || '',
          dis: rec.get('dis')?.toStr() || '',
          curVal: isAlarmActive,
          timestamp: new Date(),
          severity: parseSeverity(rec),
        });
      }
    });
  }

  return { alarms, isLoading, error };
}

function parseSeverity(rec: HDict): 'critical' | 'warning' | 'info' {
  const priority = rec.get('priority');
  const priorityVal = priority instanceof HNum ? priority.val : 99;

  if (priorityVal <= 3) return 'critical';
  if (priorityVal <= 7) return 'warning';
  return 'info';
}
```

### 2.3 useHaystackPoint — Bidirectional Point Control

Enable AI-recommended setpoint writes (with human confirmation):

```tsx
// src/hooks/useSetpointControl.ts
import { useHaystackPoint } from 'haystack-react';
import { HNum, HStr } from 'haystack-core';

export interface SetpointControl {
  currentValue: number;
  unit: string;
  recommendedValue?: number;
  isApplying: boolean;
  applyRecommendation: (value: number) => Promise<void>;
  cancelRecommendation: () => void;
}

export function useSetpointControl(pointId: string): SetpointControl {
  const [pointValue, setPointValue, updatedPoint, { isLoading, error }] =
    useHaystackPoint<HNum>(pointId);

  const currentValue = pointValue?.val || 0;
  const unit = pointValue?.unit || '';

  const applyRecommendation = async (value: number) => {
    // In FIN Framework, AI writes go to Priority 16 (requires confirmation)
    const newValue = new HNum(value, unit);
    await setPointValue(newValue);
  };

  const cancelRecommendation = () => {
    // Reset to current value
    if (pointValue) {
      setPointValue(pointValue);
    }
  };

  return {
    currentValue,
    unit,
    recommendedValue: undefined, // Set by AI optimization service
    isApplying: isLoading,
    applyRecommendation,
    cancelRecommendation,
  };
}
```

## Part 3: Enhanced Components

### 3.1 Real-Time Diagnostic Card with useWatch

```tsx
// src/components/DiagnosticCard/LiveDiagnosticCard.tsx
import { useWatch, useEval } from 'haystack-react';
import { DiagnosticCard } from './DiagnosticCard';
import { DiagnosisData } from './types';

interface LiveDiagnosticCardProps {
  alarmId: string;
  equipId: string;
}

export function LiveDiagnosticCard({ alarmId, equipId }: LiveDiagnosticCardProps) {
  // Watch all points under the equipment for real-time context
  const { grid: pointGrid } = useWatch({
    filter: `point and equipRef==@${equipId}`,
    pollRate: 2, // 2 second polling
  });

  // Trigger AI diagnosis via custom Op when alarm fires
  const { result: diagnosis, isLoading } = useEval(
    `agentDiagnose(@${alarmId}, {hisRange: "past1hr"})`
  );

  if (isLoading) {
    return <div className="diagnostic-card loading">Analyzing alarm...</div>;
  }

  if (!diagnosis) {
    return <div className="diagnostic-card waiting">Waiting for alarm data...</div>;
  }

  const diagnosisData = resultToDiagnosisData(diagnosis);

  return <DiagnosticCard diagnosis={diagnosisData} alarmId={alarmId} />;
}

function resultToDiagnosisData(result: unknown): DiagnosisData {
  // Convert Haystack result to DiagnosisData
  // Implementation depends on agentDiagnose Op response format
  return {
    fault_category: 'equipment',
    root_cause: 'example',
    explanation: 'example',
    confidence: 0.85,
    severity: 'high',
    rca_chain: [],
    affected_equipment: [],
    recommendations: [],
  };
}
```

### 3.2 Energy Optimization with Setpoint Control

```tsx
// src/components/Optimization/SetpointOptimizer.tsx
import { useReadByFilter, useEval } from 'haystack-react';
import { useSetpointControl } from '../../hooks/useSetpointControl';
import { HNum } from 'haystack-core';

export function SetpointOptimizer({ equipId }: { equipId: string }) {
  // Read current setpoints
  const { grid: setpointGrid } = useReadByFilter(
    `point and equipRef==@${equipId} and sp`
  );

  // Run AI optimization
  const { result: optimization, isLoading, error } = useEval(
    `agentOptimizeSetpoints(@${equipId}, {target: "energy"})`
  );

  if (isLoading) return <div>Computing optimal setpoints...</div>;
  if (error) return <div>Optimization failed: {error.message}</div>;

  const recommendations = parseOptimizationResult(optimization);

  return (
    <div className="setpoint-optimizer">
      <h3>Setpoint Recommendations</h3>
      {recommendations.map((rec) => (
        <SetpointControl key={rec.pointId} {...rec} />
      ))}
    </div>
  );
}

function SetpointControl({ pointId, currentValue, recommendedValue, savings }: {
  pointId: string;
  currentValue: number;
  recommendedValue: number;
  savings: number;
}) {
  const { currentValue: actualValue, unit, applyRecommendation } =
    useSetpointControl(pointId);

  return (
    <div className="setpoint-row">
      <span>{pointId}</span>
      <span>
        {actualValue} {unit} → {recommendedValue} {unit}
      </span>
      <span className="savings">Est. savings: ${savings}/yr</span>
      <button onClick={() => applyRecommendation(recommendedValue)}>
        Apply
      </button>
    </div>
  );
}

function parseOptimizationResult(result: unknown) {
  // Parse AI optimization result
  return [];
}
```

### 3.3 HMI Auto-Generation Preview

```tsx
// src/components/Hmi/HmiPreview.tsx
import { useEval } from 'haystack-react';

interface HmiLayout {
  pages: Array<{
    title: string;
    equip_type: string;
    grid_columns: number;
    grid_rows: number;
    widgets: Array<{
      label: string;
      widget_type: string;
      point_id: string;
    }>;
  }>;
}

export function HmiPreview({ equipFilter }: { equipFilter: string }) {
  // Generate HMI layout via AI agent
  const { result: layout, isLoading, error } = useEval(
    `agentGenHmiLayout("${equipFilter}", {gridColumns: 6})`
  );

  if (isLoading) return <div>Generating HMI layout...</div>;
  if (error) return <div>HMI generation failed: {error.message}</div>;

  const hmiLayout = layout as HmiLayout;

  return (
    <div className="hmi-preview">
      <h3>Generated HMI Layout</h3>
      {hmiLayout.pages.map((page, idx) => (
        <div key={idx} className="hmi-page">
          <h4>{page.title}</h4>
          <div className="hmi-grid" style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${page.grid_columns}, 1fr)`,
            gridTemplateRows: `repeat(${page.grid_rows}, 1fr)`,
          }}>
            {page.widgets.map((widget, wIdx) => (
              <HmiWidget key={wIdx} widget={widget} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function HmiWidget({ widget }: { widget: { label: string; widget_type: string; point_id: string } }) {
  const { widget_type, label, point_id } = widget;

  // Render different widget types based on widget_type
  if (widget_type === 'gauge') {
    return <GaugeWidget label={label} pointId={point_id} />;
  }
  if (widget_type === 'trend') {
    return <TrendWidget label={label} pointId={point_id} />;
  }
  if (widget_type === 'status') {
    return <StatusWidget label={label} pointId={point_id} />;
  }

  return <div>Unknown widget type: {widget_type}</div>;
}

function GaugeWidget({ label, pointId }: { label: string; pointId: string }) {
  const { grid } = useReadByFilter(`point and id==@${pointId}`);
  // Implement gauge visualization
  return <div className="gauge-widget">{label}: Gauge</div>;
}

function TrendWidget({ label, pointId }: { label: string; pointId: string }) {
  const { grid } = useReadByFilter(`point and id==@${pointId}`);
  // Implement trend chart
  return <div className="trend-widget">{label}: Trend</div>;
}

function StatusWidget({ label, pointId }: { label: string; pointId: string }) {
  const { grid } = useReadByFilter(`point and id==@${pointId}`);
  // Implement status indicator
  return <div className="status-widget">{label}: Status</div>;
}
```

## Part 4: Unit Conversion with haystack-units

```tsx
// src/utils/unitConversion.ts
import {
  celsius,
  fahrenheit,
  kelvin,
  pascal,
  kilopascal,
  bar,
  pounds_per_square_inch,
  cubic_meter_per_second,
  cubic_foot_per_minute,
  kilowatt,
  british_thermal_unit_per_hour,
  HNum,
} from 'haystack-units';

export function convertTemperature(value: number, fromUnit: string, toUnit: string): number {
  const num = new HNum(value, fromUnit);
  const targetUnit = getTemperatureUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.val;
}

export function convertPressure(value: number, fromUnit: string, toUnit: string): number {
  const num = new HNum(value, fromUnit);
  const targetUnit = getPressureUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.val;
}

export function convertFlow(value: number, fromUnit: string, toUnit: string): number {
  const num = new HNum(value, fromUnit);
  const targetUnit = getFlowUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.val;
}

export function convertPower(value: number, fromUnit: string, toUnit: string): number {
  const num = new HNum(value, fromUnit);
  const targetUnit = getPowerUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.val;
}

function getTemperatureUnit(unit: string) {
  switch (unit) {
    case '°C': case 'C': return celsius;
    case '°F': case 'F': return fahrenheit;
    case 'K': return kelvin;
    default: throw new Error(`Unknown temperature unit: ${unit}`);
  }
}

function getPressureUnit(unit: string) {
  switch (unit) {
    case 'Pa': return pascal;
    case 'kPa': return kilopascal;
    case 'bar': return bar;
    case 'psi': return pounds_per_square_inch;
    default: throw new Error(`Unknown pressure unit: ${unit}`);
  }
}

function getFlowUnit(unit: string) {
  switch (unit) {
    case 'm³/s': return cubic_meter_per_second;
    case 'CFM': case 'cfm': return cubic_foot_per_minute;
    default: throw new Error(`Unknown flow unit: ${unit}`);
  }
}

function getPowerUnit(unit: string) {
  switch (unit) {
    case 'kW': return kilowatt;
    case 'Btu/h': case 'BTUH': return british_thermal_unit_per_hour;
    default: throw new Error(`Unknown power unit: ${unit}`);
  }
}
```

## Part 5: HFilter for Advanced Queries

```tsx
// src/hooks/useFilteredPoints.ts
import { HFilter } from 'haystack-core';
import { useReadByFilter } from 'haystack-react';

export function useFilteredPoints(filters: {
  equipType?: string;
  pointKind?: string;
  valueRange?: { min: number; max: number };
  unit?: string;
}) {
  // Build HFilter programmatically for complex queries
  let filterExpr = 'point';

  if (filters.equipType) {
    filterExpr += ` and equipRef->equip==${filters.equipType}`;
  }

  if (filters.pointKind) {
    filterExpr += ` and kind==${filters.pointKind}`;
  }

  if (filters.valueRange) {
    filterExpr += ` and curVal>=${filters.valueRange.min} and curVal<=${filters.valueRange.max}`;
  }

  if (filters.unit) {
    filterExpr += ` and unit==${filters.unit}`;
  }

  const { grid, isLoading, error } = useReadByFilter(filterExpr);

  return { points: grid, isLoading, error };
}

// Example usage:
// const { points } = useFilteredPoints({
//   equipType: 'ahu',
//   pointKind: 'sensor',
//   valueRange: { min: 18, max: 26 },
//   unit: '°C'
// });
```

## Part 6: TypeScript Type Integration

```tsx
// src/types/haystack.ts
import { HVal, HDict, HGrid, HNum, HStr, HBool, HRef, HDateTime } from 'haystack-core';

// Extend Haystack types with baAgent-specific markers
export interface BaDict extends HDict {
  get(tag: 'alarmId'): HRef | null;
  get(tag: 'faultCategory'): HStr | null;
  get(tag: 'confidence'): HNum | null;
  get(tag: 'severity'): HStr | null;
  get(tag: 'timestamp'): HDateTime | null;
}

export interface AlarmGrid extends HGrid {
  rows: Map<string, BaDict>;
}

// Helper to convert Haystack Grid to baAgent types
export function gridToDiagnosisData(grid: HGrid): DiagnosisData[] {
  return grid.rows.map((row) => {
    const dict = row.toDict();
    return {
      fault_category: dict.get('fault_category')?.toStr() || 'unknown',
      root_cause: dict.get('root_cause')?.toStr() || '',
      explanation: dict.get('explanation')?.toStr() || '',
      confidence: dict.get('confidence') instanceof HNum
        ? dict.get('confidence')!.val
        : 0,
      severity: dict.get('severity')?.toStr() || 'medium',
      rca_chain: [],
      affected_equipment: [],
      recommendations: [],
    };
  });
}
```

## Part 7: Error Handling & Retry Logic

```tsx
// src/hooks/useHaystackWithRetry.ts
import { useEffect, useState } from 'react';
import { useHaystackClient } from '../contexts/HaystackContext';

export function useHaystackWithRetry<T>(
  fetcher: () => Promise<T>,
  options: { maxRetries?: number; retryDelay?: number } = {}
) {
  const { client } = useHaystackClient();
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const { maxRetries = 3, retryDelay = 1000 } = options;

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetcher();
        if (!cancelled) {
          setData(result);
          setIsLoading(false);
        }
      } catch (err) {
        if (cancelled) return;

        const error = err instanceof Error ? err : new Error(String(err));

        if (retryCount < maxRetries) {
          // Retry after delay
          setTimeout(() => {
            setRetryCount((prev) => prev + 1);
          }, retryDelay * (retryCount + 1)); // Exponential backoff
        } else {
          setError(error);
          setIsLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [fetcher, retryCount, maxRetries, retryDelay]);

  return { data, isLoading, error, retry: () => setRetryCount(0) };
}
```

## Quick Reference: Hook Mapping

| baAgentUI Feature | haystack-react Hook | Description |
|------------------|---------------------|-------------|
| Alarm monitoring | `useWatch({filter: 'alarm and curVal'})` | Real-time alarm subscription |
| Equipment context | `useReadByFilter('equip and siteRef==@x')` | Query equipment records |
| Point values | `useHaystackPoint(pointId)` | Bidirectional point binding |
| AI diagnosis | `useEval('agentDiagnose(@x)')` | Invoke custom Ops |
| Optimization | `useEval('agentOptimizeSetpoints(@x)')` | AI setpoint optimization |
| HMI generation | `useEval('agentGenHmiLayout("ahu")')` | Auto-generate layouts |
| Sensor health | `useEval('agentInspect("sensor")')` | Virtual inspection |

## Next Steps

1. **Install dependencies**: `npm install haystack-core haystack-units haystack-nclient haystack-react`
2. **Implement HaystackProvider** in App.tsx for client sharing
3. **Replace mock API calls** with haystack-react hooks in existing components
4. **Add unit conversion** utilities using haystack-units
5. **Implement HFilter-based queries** for advanced filtering
6. **Create retry logic** for resilient network communication
