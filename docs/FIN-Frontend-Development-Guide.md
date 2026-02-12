# FIN Framework Frontend Development Guide for baAgentUI

> Based on J2 Innovations FIN Framework 5.2 documentation and patterns

## Overview

FIN Framework provides a **dual-route frontend architecture** for baAgentUI:

1. **Route A: Ractive.js Widgets** — Embedded within FIN Graphics Builder for lightweight custom graphics
2. **Route B: React SPA** — Standalone app mounted via FIN WebMod for rich AI interaction UI

This guide covers both approaches and how to integrate them with the Haxall/FIN backend.

---

## Part 1: Ractive.js Widget Development (FIN Graphics Builder)

### 1.1 What is Ractive.js in FIN?

FIN Framework embeds **Ractive.js** as its template-driven UI engine for custom widgets. Ractive provides:
- Declarative templates with Mustache-like syntax
- Two-way data binding (bidirectional by default)
- Computed properties
- Event handling
- SVG-based graphics

### 1.2 The FIN Graphics Builder Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  FIN Graphics Builder                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Ractive Editor                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Template   │  │ Model       │                  │   │
│  │  │ (HTML/SVG) │  │ (Data)      │                  │   │
│  │  └─────────────┘  └─────────────┘                  │   │
│  │                                                     │   │
│  │  Yellow text = Editable via property sheet          │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↕                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Haystack Tag Binding                              │   │
│  │  equipRef, pointRef, navId → Widget Properties    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Creating a Custom Widget: SVG Bar Gauge Example

#### Template (HTML/SVG)

```html
<!-- Ractive template for Bar Gauge -->
<div class="bar-gauge-container">
  <svg width="100%" height="100%" viewBox="0 0 200 40">
    <!-- Background track -->
    <rect x="10" y="15" width="180" height="10" fill="#e0e0e0" rx="5" />

    <!-- Normal range (green) -->
    <rect x="{{normalStart}}" y="15" width="{{normalWidth}}" height="10" fill="#4caf50" rx="5" />

    <!-- Warning range (yellow) -->
    <rect x="{{warningStart}}" y="15" width="{{warningWidth}}" height="10" fill="#ff9800" rx="5" />

    <!-- Critical range (red) -->
    <rect x="{{criticalStart}}" y="15" width="{{criticalWidth}}" height="10" fill="#f44336" rx="5" />

    <!-- Value indicator -->
    <circle cx="{{valuePos}}" cy="20" r="8" fill="#333" stroke="#fff" stroke-width="2" />

    <!-- Value text -->
    <text x="100" y="36" text-anchor="middle" font-size="12">
      {{formattedValue}}
    </text>
  </svg>

  <!-- Label from Haystack -->
  <div class="gauge-label">{{label}}</div>
</div>
```

#### Model (JavaScript)

```javascript
// Ractive component initialization
Ractive.components['barGauge'] = Ractive.extend({
  template: '#bar-gauge-template',

  data: {
    // Editable properties (exposed via property sheet)
    label: 'Temperature',
    unit: '°C',
    minValue: 0,
    maxValue: 100,

    // Range thresholds
    normalMax: 70,
    warningMax: 90,

    // Current value (bound to Haystack point)
    value: 0,

    // Computed properties
    formattedValue: function() {
      return this.get('value').toFixed(1) + ' ' + this.get('unit');
    },

    valuePos: function() {
      var pct = (this.get('value') - this.get('minValue')) /
                (this.get('maxValue') - this.get('minValue'));
      return 10 + (pct * 180);
    }
  }
});
```

#### Haystack Tag Binding

To make widget properties editable via the FIN property sheet, add tags to your graphic definition:

```javascript
// In your View definition in Graphics Builder
{
  name: "barGauge",
  tags: {
    // These tags expose properties to the property sheet
    label: { type: "str", def: "Temperature" },
    unit: { type: "str", def: "°C" },
    pointRef: { type: "ref" },  // Bind to Haystack point
    normalMax: { type: "number", def: 70 },
    warningMax: { type: "number", def: 90 },
    maxValue: { type: "number", def: 100 }
  }
}
```

### 1.4 Real-Time Data Binding with Haystack Points

FIN automatically pushes point value changes to bound widgets:

```javascript
// Subscribe to point value updates
ractive.on('init', function() {
  var pointRef = this.get('pointRef');

  if (pointRef) {
    // FIN handles the subscription automatically
    // When point changes, Ractive updates the UI
    this.observe('pointRef', function(newRef) {
      // Re-subscribe if reference changes
    });
  }
});
```

---

## Part 2: React SPA Development (FIN WebMod Integration)

### 2.1 WebMod Architecture

FIN Framework supports mounting external web applications via **WebMod**:

```
┌─────────────────────────────────────────────────────────────┐
│  FIN Framework (Haxall)                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WebMod Configuration                               │   │
│  │  /baAgentUI → /path/to/baAgentUI/dist               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         ↕ (REST API)
┌─────────────────────────────────────────────────────────────┐
│  baAgentUI (React SPA)                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Chat        │  │ Diagnostic  │  │ 3D Topology  │       │
│  │ Interface   │  │ Cards       │  │ Visualizer   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Haystack REST API Integration

FIN exposes all Haystack Ops as HTTP endpoints:

```typescript
// api/haystack.ts
interface HaystackResponse<T> = {
  ok: boolean;
  _meta?: Record<string, unknown>;
  error?: string;
  data?: T;
}

export class HaystackClient {
  constructor(
    private baseUrl: string,
    private username: string,
    private password: string
  ) {}

  async eval(expr: string): Promise<HaystackResponse<unknown>> {
    const response = await fetch(`${this.baseUrl}/api/haystack/eval`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${btoa(`${this.username}:${this.password}`)}`
      },
      body: JSON.stringify({ expr })
    });
    return response.json();
  }

  async invokeOp(opName: string, payload: unknown): Promise<HaystackResponse<unknown>> {
    const response = await fetch(`${this.baseUrl}/api/${opName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${btoa(`${this.username}:${this.password}`)}`
      },
      body: JSON.stringify(payload)
    });
    return response.json();
  }
}
```

### 2.3 Connecting baAgentUI to AI Agent Ops

```typescript
// api/baAgent.ts
import { HaystackClient } from './haystack';
import { DiagnosisData } from '@/components/DiagnosticCard/types';

export class BaAgentClient {
  private client: HaystackClient;

  constructor(config: { baseUrl: string; username: string; password: string }) {
    this.client = new HaystackClient(config.baseUrl, config.username, config.password);
  }

  async diagnoseAlarm(alarmId: string, opts?: { hisRange?: string; message?: string }): Promise<DiagnosisData> {
    const response = await this.client.invokeOp('agentDiagnose', {
      alarmRef: alarmId,
      ...opts
    });

    if (!response.ok || !response.data) {
      throw new Error(response.error || 'Diagnosis failed');
    }

    return response.data as DiagnosisData;
  }

  async optimizeSetpoints(equipId: string, opts?: { target?: string; hisRange?: string }) {
    return this.client.invokeOp('agentOptimizeSetpoints', {
      equipRef: equipId,
      ...opts
    });
  }

  async generateHmiLayout(filter: string, opts?: { gridColumns?: number }) {
    return this.client.invokeOp('agentGenHmiLayout', { filter, ...opts });
  }
}
```

### 2.4 WebSocket Integration for Real-Time Updates

FIN 5.2 supports WebSocket subscriptions for real-time data:

```typescript
// hooks/useHaystackSubscription.ts
import { useEffect, useState } from 'react';

interface PointValue {
  id: string;
  val: unknown;
  timestamp: string;
}

export function useHaystackSubscription(pointIds: string[]) {
  const [values, setValues] = useState<Map<string, PointValue>>(new Map());
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost/api/haystack/watch`);

    ws.onopen = () => {
      setConnected(true);
      // Subscribe to points
      ws.send(JSON.stringify({
        action: 'subscribe',
        ids: pointIds
      }));
    };

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setValues((prev) => {
        const next = new Map(prev);
        next.set(update.id, update);
        return next;
      });
    };

    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [pointIds]);

  return { values, connected };
}
```

---

## Part 3: FIN 5.2 Mobile-Optimized UI/UX Patterns

### 3.1 Design Principles

FIN 5.2 introduced **mobile-optimized consistent UI/UX** across all apps:

| Principle | Description | baAgentUI Implementation |
|-----------|-------------|--------------------------|
| Touch-Friendly | Minimum 44x44px tap targets | Button and card sizing |
| Responsive | Works on phones, tablets, desktops | CSS Grid + Flexbox |
| Card-Based | Information grouped in swipeable cards | DiagnosticCard component |
| Consistent Navigation | Bottom tab bar on mobile | App shell navigation |
| Dark Mode | Automatic system theme detection | CSS custom properties |

### 3.2 Card-Based Layout Pattern

```css
/* FIN 5.2 inspired card styling */
.diagnostic-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 16px;
  background: var(--card-bg, #ffffff);
  transition: transform 0.2s, box-shadow 0.2s;
}

.diagnostic-card:active {
  transform: scale(0.98);
}

@media (max-width: 768px) {
  .diagnostic-card {
    border-radius: 12px;
    padding: 20px;
  }
}
```

### 3.3 Bottom Navigation (Mobile)

```tsx
// components/MobileNav.tsx
export function MobileNav() {
  return (
    <nav className="mobile-nav">
      <NavLink to="/diagnostics">
        <Icon name="diagnostics" />
        <span>Diagnostics</span>
      </NavLink>
      <NavLink to="/optimize">
        <Icon name="optimize" />
        <span>Optimize</span>
      </NavLink>
      <NavLink to="/inspect">
        <Icon name="inspect" />
        <span>Inspect</span>
      </NavLink>
      <NavLink to="/hmi">
        <Icon name="hmi" />
        <span>HMI</span>
      </NavLink>
    </nav>
  );
}

.mobile-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  padding: 8px 0;
  background: var(--surface-color);
  border-top: 1px solid var(--border-color);
}
```

---

## Part 4: Dual-Route Architecture Implementation

### 4.1 When to Use Each Route

| Use Case | Recommended Route |
|----------|------------------|
| Simple gauge displays in standard HMI views | Ractive.js (Graphics Builder) |
| Complex AI diagnostic cards with rich interactions | React SPA (WebMod) |
| Building operator dashboards | Ractive.js |
| AI chat interface | React SPA |
| Real-time point value displays | Ractive.js |
| 3D topology visualization | React SPA |
| Mobile-responsive AI operations | React SPA |

### 4.2 Hybrid Approach Example

Create a Ractive widget that embeds the React app for complex interactions:

```html
<!-- Ractive widget container -->
<div class="ba-agent-widget">
  <iframe
    src="/baAgentUI/index.html?embedded=true&point={{pointId}}"
    width="100%"
    height="400px"
    frameborder="0">
  </iframe>
</div>
```

---

## Part 5: Development Workflow

### 5.1 Local Development Setup

```bash
# 1. Start Haxall/FIN with Docker Compose
docker compose up -d haxall

# 2. Start React dev server (Vite)
cd src/baAgentUI
npm run dev

# 3. Configure proxy in vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // FIN Haystack API
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8080',    // FIN WebSocket
        ws: true
      }
    }
  }
});
```

### 5.2 Production Build

```bash
# Build React app
npm run build

# Copy to FIN WebMod directory
cp -r dist /path/to/fincruise/webs/baAgentUI

# Or configure Docker volume mount
# docker-compose.yml:
# services:
#   haxall:
#     volumes:
#       - ./src/baAgentUI/dist:/usr/share/haxall/webs/baAgentUI:ro
```

---

## Part 6: Component Library for baAgentUI

### 6.1 Core Components

```tsx
// components/index.ts
export { DiagnosticCard } from './DiagnosticCard';
export { ConfidenceBar } from './ConfidenceBar';
export { SeverityBadge } from './SeverityBadge';
export { RcaChain } from './RcaChain';

// Hooks
export { useHaystackSubscription } from '../hooks/useHaystackSubscription';
export { useDiagnosis } from '../hooks/useDiagnosis';

// API
export { BaAgentClient } from '../api/baAgent';
```

### 6.2 FIN-Style Icon System

FIN uses Material Icons. Import via:

```tsx
import Icon from '@mdi/react';
import { mdiAlertCircle, mdiCheckCircle, mdiClock } from '@mdi/js';

<Icon path={mdiAlertCircle} size={1} />
```

---

## Part 7: Testing Strategy

### 7.1 Unit Tests (React Components)

```typescript
// DiagnosticCard.test.tsx
import { render, screen } from '@testing-library/react';
import { DiagnosticCard } from './DiagnosticCard';

describe('DiagnosticCard', () => {
  it('displays confidence percentage', () => {
    const mockDiagnosis: DiagnosisData = {
      fault_category: 'sensor',
      root_cause: 'Temperature sensor failure',
      explanation: 'Sensor reading frozen',
      confidence: 0.85,
      severity: 'high',
      rca_chain: [],
      affected_equipment: ['AHU-01'],
      recommendations: ['Replace sensor']
    };

    render(<DiagnosticCard diagnosis={mockDiagnosis} />);
    expect(screen.getByText('85%')).toBeInTheDocument();
  });
});
```

### 7.2 E2E Tests (Haystack Integration)

```typescript
// tests/e2e/diagnose.e2e.ts
import { test, expect } from '@playwright/test';

test('diagnose alarm via Haystack Op', async ({ request }) => {
  const response = await request.post('/api/agentDiagnose', {
    data: {
      alarmRef: '@alarm-123',
      hisRange: 'yesterday'
    }
  });

  expect(response.ok()).toBeTruthy();
  const result = await response.json();
  expect(result.ok).toBe(true);
  expect(result.data.confidence).toBeGreaterThan(0);
});
```

---

## Part 8: Performance Considerations

### 8.1 FIN Graphics Builder Performance

- **Debounce rapid updates**: Use Ractive's `ractive.update(true)` for batch updates
- **SVG optimization**: Limit SVG element count per widget (< 500 elements recommended)
- **Virtual scrolling**: For large point lists, use FIN's built-in virtual scrolling

### 8.2 React SPA Performance

- **Code splitting**: Lazy load diagnostic, optimization, and inspection modules
- **Memoization**: Use React.memo for expensive diagnostic card renders
- **WebSocket throttling**: Limit update frequency to 1Hz for fast-changing points

---

## Part 9: Security & Authentication

### 9.1 FIN OpenID Connect Integration

```typescript
// Configure React to use FIN's OIDC
const authConfig = {
  authority: 'https://fin-server/auth',
  client_id: 'baAgentUI',
  redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile haystack:read haystack:write'
};
```

### 9.2 API Token Authentication

```typescript
// Alternative: Use API tokens for service accounts
const client = new HaystackClient(
  baseUrl,
  'username',  // Or API token
  'password'
);
```

---

## Quick Reference: FIN Widget Development vs React SPA

| Aspect | Ractive.js (FIN Graphics Builder) | React SPA (WebMod) |
|--------|----------------------------------|--------------------|
| **Setup** | Built into FIN | Separate build process |
| **Data Binding** | Automatic via Haystack tags | Manual via fetch/WebSocket |
| **Real-time Updates** | Built-in subscription | WebSocket required |
| **Mobile Support** | Responsive via CSS | Full control |
| **Complex Interactions** | Limited | Full React ecosystem |
| **Development Speed** | Fast for simple graphics | Slower for simple things |
| **Deploy** | Part of FIN database | Static file mount |
| **Best For** | Gauges, displays, dashboards | AI chat, complex forms, 3D |

---

## Next Steps

1. **Implement DiagnosticCard** with FIN 5.2 mobile-optimized styling
2. **Create Ractive widget** for quick point value displays
3. **Set up WebSocket subscription** for real-time AI diagnosis updates
4. **Configure WebMod** to mount React app in FIN
5. **Test Haystack Op integration** with existing agentDiagnose endpoint
