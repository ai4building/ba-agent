// ============================================================
// BA Agent - Modern Chat Interface
// ============================================================

import { useState, useEffect, useRef } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Copy,
  Check,
  Activity,
  AlertTriangle,
  Layout,
  Database,
  X,
  ShieldCheck,
  ExternalLink,
  Cpu,
  Zap,
  Paperclip,
  Maximize2,
  Menu,
  Wrench,
  Play,
  Settings,
  Tags,
  Sparkles,
} from 'lucide-react';
import {
  readEntities,
  getAbout,
  formatHaystackValue,
  HGrid,
  valueIsKind,
  Kind,
} from './services/haystack';

// ============================================================
// Types
// ============================================================

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface SystemStatus {
  fantom: 'Connected' | 'Disconnected';
  python: 'Active' | 'Standby';
  folio: 'OK' | 'Error';
  llm?: 'enabled' | 'disabled';
}

interface DiagnosticDetails {
  step1: string;
  step2: string;
  step3?: string;
  rootCause?: string;
  commandState?: string;
  sensorFeedback?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  type: 'text' | 'analysis' | 'options' | 'hmi' | 'diagnosis' | 'tagging' | 'grid';
  content: string;
  timestamp: string;
  options?: MessageOption[];
  verified?: boolean;
  gridData?: HGrid;
  gridTitle?: string;
  // LLM related fields
  llmConfidence?: number;
  llmThought?: string;
  llmEnabled?: boolean;
}

interface MessageOption {
  label: string;
  value: string;
}

// Grid Table Column Info
interface GridColumn {
  name: string;
  displayName?: string;
  kind?: string;
}

interface HmiComponent {
  type: string;
  id: string;
  label: string;
}

interface HmiLayout {
  device: string;
  binding: string;
  components: HmiComponent[];
}

// ============================================================
// Initial Messages
// ============================================================

const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'assistant',
    type: 'text',
    content: '您好，我是建筑运维辅助 Agent。系统已初始化。',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    verified: true,
  },
];

// ============================================================
// Sub Components
// ============================================================

// Status Item for Sidebar
interface StatusItemProps {
  label: string;
  value: string;
  status?: 'online' | 'idle' | 'offline';
}

const StatusItem = ({ label, value, status = 'online' }: StatusItemProps) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', fontSize: '12px' }}>
    <span style={{ color: '#94a3b8' }}>{label}</span>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ fontFamily: 'monospace', color: '#e2e8f0' }}>{value}</span>
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: status === 'online' ? '#10b981' : status === 'idle' ? '#f59e0b' : '#ef4444',
          boxShadow: status === 'online' ? '0 0 8px rgba(16,185,129,0.6)' : 'none'
        }}
      />
    </div>
  </div>
);

// Diagnosis Card Component
interface DiagnosisCardProps {
  data?: DiagnosticDetails;
  onExecute?: (action: string) => void;
}

const DiagnosisCardInline = ({ data, onExecute }: DiagnosisCardProps) => (
  <div style={{ marginTop: '12px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
    <div style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', borderBottom: '1px solid #334155', padding: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
      <AlertTriangle size={16} style={{ color: '#f59e0b' }} />
      <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#f59e0b' }}>检测到物理矛盾</span>
    </div>
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <div style={{ backgroundColor: 'rgba(30, 41, 59, 0.5)', padding: '12px', borderRadius: '8px', border: '1px solid #334155' }}>
          <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>Command State</div>
          <div style={{ fontSize: '14px', color: '#e2e8f0' }}>{data?.commandState || '风阀开度: 100%'}</div>
        </div>
        <div style={{ backgroundColor: 'rgba(30, 41, 59, 0.5)', padding: '12px', borderRadius: '8px', border: '1px solid #334155' }}>
          <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>Sensor Feedback</div>
          <div style={{ fontSize: '14px', color: '#f43f5e', fontWeight: 'bold', fontFamily: 'monospace' }}>
            {data?.sensorFeedback || '气流值: 0.05 L/s'}
          </div>
        </div>
      </div>
      <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.5', fontStyle: 'italic', borderLeft: '2px solid #475569', paddingLeft: '12px' }}>
        "Python 逻辑分析：风阀指令与反馈气流严重不匹配。推测执行机构机械锁定或连杆脱落。"
      </p>
      <div style={{ display: 'flex', gap: '8px', paddingTop: '8px' }}>
        <button
          onClick={() => onExecute?.('生成维保工单')}
          style={{ flex: 1, padding: '8px 16px', backgroundColor: '#2563eb', color: 'white', borderRadius: '8px', fontSize: '12px', fontWeight: '500', border: 'none', cursor: 'pointer', transition: 'background-color 0.2s' }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#3b82f6'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
        >
          <Wrench size={14} /> 生成维保工单
        </button>
        <button
          onClick={() => onExecute?.('发起复位测试')}
          style={{ flex: 1, padding: '8px 16px', backgroundColor: '#334155', color: 'white', borderRadius: '8px', fontSize: '12px', fontWeight: '500', border: 'none', cursor: 'pointer', transition: 'background-color 0.2s' }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#475569'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#334155'}
        >
          <Play size={14} /> 发起复位测试
        </button>
      </div>
    </div>
  </div>
);

// HMI Preview Card
interface HmiPreviewCardProps {
  layout?: HmiLayout;
  onConfirm?: () => void;
}

const HmiPreviewCard = ({ layout, onConfirm }: HmiPreviewCardProps) => (
  <div style={{ marginTop: '12px', backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.1)' }}>
    <div style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#334155', fontWeight: 'bold', fontSize: '14px' }}>
        <Layout size={16} style={{ color: '#2563eb' }} />
        HMI 自动化生成预览 (Canvas)
      </div>
      <button style={{ backgroundColor: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8', transition: 'color 0.2s' }}>
        <Maximize2 size={14} />
      </button>
    </div>
    <div style={{ padding: '24px', backgroundColor: '#f0f2f5', minHeight: '160px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      {/* Mock Component */}
      <div style={{ width: '100%', maxWidth: '280px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', padding: '16px', border: '1px solid #e2e8f0', position: 'relative' }}>
        <div style={{ position: 'absolute', top: '8px', right: '8px', display: 'flex', gap: '4px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#e2e8f0' }}></div>
        </div>
        <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#2563eb', marginBottom: '8px' }}>{layout?.device || 'AHU_Cooling_Coil'}</div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px' }}>
          <div style={{ width: '32px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '4px 0 4px 0', position: 'relative', borderLeft: '2px solid #3b82f6', borderTop: '2px solid #3b82f6' }}>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-around', padding: '0 4px' }}>
              <div style={{ height: '2px', backgroundColor: '#93c5fd', width: '100%' }}></div>
              <div style={{ height: '2px', backgroundColor: '#93c5fd', width: '100%' }}></div>
              <div style={{ height: '2px', backgroundColor: '#93c5fd', width: '100%' }}></div>
            </div>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ height: '6px', width: '100%', backgroundColor: '#f1f5f9', borderRadius: '999px', overflow: 'hidden' }}>
              <div style={{ height: '100%', backgroundColor: '#3b82f6', width: '65%' }}></div>
            </div>
            <div style={{ fontSize: '10px', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
              <span>Valve: 65%</span>
              <span style={{ color: '#2563eb', fontFamily: 'monospace' }}>12.5°C</span>
            </div>
          </div>
        </div>
      </div>
      {/* Semantic Tags Overlay */}
      <div style={{ position: 'absolute', bottom: '8px', left: '8px', display: 'flex', gap: '4px' }}>
        <span style={{ padding: '2px 6px 2px', backgroundColor: '#2563eb', color: 'white', fontSize: '8px', borderRadius: '4px', fontFamily: 'monospace' }}>
          chilledWaterCooling
        </span>
        <span style={{ padding: '2px 6px 2px', backgroundColor: '#2563eb', color: 'white', fontSize: '8px', borderRadius: '4px', fontFamily: 'monospace' }}>modulating</span>
      </div>
    </div>
    <div style={{ padding: '12px', backgroundColor: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
      <button
        onClick={onConfirm}
        style={{ padding: '8px 16px', backgroundColor: '#059669', color: 'white', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#047857'}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#059669'}
      >
        发布到 FIN
      </button>
    </div>
  </div>
);

// Auto-Tagging Display
const AutoTaggingCard = () => (
  <div style={{ marginTop: '12px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
      <Tags size={14} style={{ color: '#4f46e5' }} />
      <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#1f2937', textDecoration: 'underline', textDecorationColor: 'rgba(79, 70, 229, 0.2)' }}>
        Haystack 4.0 标签推荐
      </span>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ fontSize: '10px', color: '#64748b', fontFamily: 'monospace', backgroundColor: 'white', padding: '8px', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
        Raw String: "CBD_T1_L12_AHU01_SF_SPD"
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {['ahu', 'fan', 'discharge', 'air', 'speed', 'sensor', 'sp'].map((tag) => (
          <span
            key={tag}
            style={{ padding: '4px 8px 2px', backgroundColor: '#eef2ff', color: '#4338ca', border: '1px solid #c7d2fe', borderRadius: '4px', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', transition: 'background-color 0.2s' }}
          >
            {tag} <Check size={10} style={{ color: '#10b981' }} />
          </span>
        ))}
        <span style={{ padding: '4px 8px 2px', backgroundColor: '#e2e8f0', color: '#64748b', borderRadius: '4px', fontSize: '10px', cursor: 'pointer' }}>
          + Add
        </span>
      </div>
      <div style={{ fontSize: '10px', color: '#059669', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <Activity size={10} /> 置信度: 98.4%
      </div>
    </div>
  </div>
);

// ============================================================
// Grid Table Component
// ============================================================

interface GridTableProps {
  grid: HGrid;
  title?: string;
  subtitle?: string;
  onRowClick?: (row: Record<string, any>) => void;
}

const GridTable = ({ grid, title = '查询结果', subtitle, onRowClick }: GridTableProps) => {
  // Helper: safely get value from HVal
  const safeValueOf = (val: any): string => {
    if (val == null) return '';
    try {
      return val.valueOf ? String(val.valueOf()) : String(val);
    } catch {
      return String(val);
    }
  };

  // Helper: get column display name
  const getColDisplayName = (name: string): string => {
    const displayNames: Record<string, string> = {
      'id': 'ID',
      'dis': '名称',
      'navName': '导航名称',
      'area': '区域',
      'floor': '楼层',
      'zone': '分区',
      'site': '站点',
      'equip': '设备',
      'point': '点位',
      'type': '类型',
      'kind': '种类',
      'status': '状态',
      'val': '当前值',
      'cur': '当前值',
      'unit': '单位',
      'temp': '温度',
      'flow': '流量',
      'pressure': '压力',
      'humidity': '湿度',
      'geoAddr': '地址',
      'geoCity': '城市',
      'geoCoord': '坐标',
      'geoCountry': '国家',
      'geoState': '省份',
      'tz': '时区',
      'weather': '天气',
      'highlights': '亮点',
      'mod': '修改时间',
    };
    return displayNames[name] || name;
  };

  // Extract columns from grid - handle both HGrid object and plain JS object
  const getColumns = (): GridColumn[] => {
    // First try: access grid.cols directly (for plain JS objects from API)
    if ((grid as any).cols && Array.isArray((grid as any).cols)) {
      const cols = (grid as any).cols;
      console.log('[GridTable] Using grid.cols:', cols);
      return cols.map((c: any) => ({
        name: c.name,
        displayName: getColDisplayName(c.name),
        kind: c.kind
      }));
    }

    // Second try: from meta.cols
    try {
      const meta = grid.meta;
      if (meta && typeof meta.isEmpty === 'function' && !meta.isEmpty()) {
        const colsVal = meta.get('cols');
        if (colsVal != null && valueIsKind(colsVal, Kind.List)) {
          const colsList: any[] = [...(colsVal as any)];
          const cols: GridColumn[] = [];

          for (const item of colsList) {
            if (item == null) continue;
            try {
              if (valueIsKind(item, Kind.Dict)) {
                const nameVal = (item as any).get('name');
                if (nameVal != null) {
                  const name = safeValueOf(nameVal);
                  const disVal = (item as any).get('dis');
                  const displayName = disVal != null ? safeValueOf(disVal) : getColDisplayName(name);
                  const kindVal = (item as any).get('kind');
                  const kind = kindVal != null ? safeValueOf(kindVal) : undefined;
                  cols.push({ name, displayName, kind });
                }
              }
            } catch {
              continue;
            }
          }
          if (cols.length > 0) {
            console.log('[GridTable] Using meta.cols:', cols);
            return cols;
          }
        }
      }
    } catch (e) {
      console.log('[GridTable] Error getting meta.cols:', e);
    }

    // Third try: get from first row keys
    try {
      const firstRow = grid.get(0);
      if (firstRow && typeof firstRow.isEmpty === 'function' && !firstRow.isEmpty()) {
        const keys = firstRow.keys;
        if (keys && Array.isArray(keys) && keys.length > 0) {
          console.log('[GridTable] Using row keys:', keys);
          return keys.map((key: string) => ({ name: key, displayName: getColDisplayName(key) }));
        }
      }
    } catch (e) {
      console.log('[GridTable] Error getting first row keys:', e);
    }

    console.log('[GridTable] No columns found');
    return [];
  };

  // Format cell value for display
  const formatCellValue = (val: any): string => {
    if (val == null) return '-';

    try {
      // Use the formatHaystackValue function which handles all types
      return formatHaystackValue(val);
    } catch {
      // Fallback to direct value extraction
      try {
        const v = val.valueOf ? val.valueOf() : val;
        return String(v);
      } catch {
        return '';
      }
    }
  };

  // Get cell styling based on value type
  const getValueStyle = (val: any): React.CSSProperties => {
    if (val == null) return { color: '#94a3b8' };

    try {
      if (valueIsKind(val, Kind.Number)) {
        return { fontFamily: 'monospace', color: '#2563eb' };
      }
      if (valueIsKind(val, Kind.Bool)) {
        // Type assertion since we know val is not null here
        const numVal = val as any;
        const boolVal = (numVal.valueOf && numVal.valueOf()) || false;
        return { color: boolVal ? '#10b981' : '#ef4444', fontWeight: 'bold' };
      }
      if (valueIsKind(val, Kind.Ref)) {
        return { color: '#8b5cf6', fontFamily: 'monospace' };
      }
      if (valueIsKind(val, Kind.Symbol)) {
        return { color: '#f59e0b', fontFamily: 'monospace' };
      }
      if (valueIsKind(val, Kind.Marker)) {
        return { color: '#64748b' };
      }
      if (valueIsKind(val, Kind.Str)) {
        return { color: '#334155' };
      }
      if (valueIsKind(val, Kind.DateTime) || valueIsKind(val, Kind.Date)) {
        return { fontFamily: 'monospace', fontSize: '11px', color: '#64748b' };
      }
    } catch {
      // Fall through to default
    }
    return { color: '#334155' };
  };

  const columns = getColumns();

  // Get all rows - handle both HGrid object and plain JS object
  const allRows: any[] = [];
  try {
    // First try: access grid.rows directly (for plain JS objects from API)
    if ((grid as any).rows && Array.isArray((grid as any).rows)) {
      allRows.push(...(grid as any).rows);
      console.log('[GridTable] Using grid.rows:', allRows.length);
    } else {
      // Second try: use HGrid iteration
      for (const row of grid) {
        allRows.push(row);
      }
      console.log('[GridTable] Using HGrid iteration:', allRows.length);
    }
  } catch (e) {
    console.log('[GridTable] Error getting rows:', e);
    // Last resort: try get(index)
    for (let i = 0; i < 1000; i++) {
      try {
        const row = grid.get(i);
        if (row == null || row.isEmpty()) break;
        allRows.push(row);
      } catch {
        break;
      }
    }
  }

  const rows = allRows.slice(0, 100);
  const totalRows = allRows.length;

  // Debug logging
  if (typeof window !== 'undefined') {
    console.log('[GridTable] columns:', columns);
    console.log('[GridTable] rows:', rows.length);
    console.log('[GridTable] firstRow:', rows[0]);
  }

  if (columns.length === 0) {
    return (
      <div style={{ marginTop: '12px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', textAlign: 'center' }}>
        <span style={{ color: '#94a3b8', fontSize: '12px' }}>无数据列 (共 {totalRows} 行)</span>
      </div>
    );
  }

  // Priority columns to display first (key columns for building automation)
  const priorityColumns = [
    'id', 'dis', 'name', 'navName',
    'equip', 'point', 'site',
    'floor', 'area', 'zone',
    'type', 'kind',
    'status', 'alarm', 'fault',
    'val', 'cur', 'curStatus',
    'unit', 'units',
    'temp', 'temperature',
    'flow', 'airFlow',
    'pressure', 'staticPressure',
    'humidity', 'rh',
    'co2', 'carbonDioxide',
    'setpoint', 'sp',
    'enabled', 'active', 'run',
    'af', 'ahuRef', 'siteRef',
  ];

  // Sort columns: priority columns first, then alphabetically
  const sortedColumns = [...columns].sort((a, b) => {
    const aIndex = priorityColumns.indexOf(a.name);
    const bIndex = priorityColumns.indexOf(b.name);
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    return a.name.localeCompare(b.name);
  });

  // Display columns: show priority columns + up to 8 total columns
  const displayColumns = sortedColumns.slice(0, 10);

  return (
    <div style={{ marginTop: '12px', backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
      {/* Header */}
      <div style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={16} style={{ color: '#2563eb' }} />
            <span style={{ fontWeight: 'bold', color: '#1e293b', fontSize: '14px' }}>{title}</span>
          </div>
          {subtitle && (
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', marginLeft: '24px' }}>{subtitle}</div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
            {totalRows} 行 × {columns.length} 列
          </span>
          {totalRows > 100 && (
            <span style={{ fontSize: '10px', color: '#f59e0b', backgroundColor: '#fef3c7', padding: '2px 6px', borderRadius: '4px' }}>
              显示前 100 行
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', maxWidth: '100%' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f1f5f9' }}>
              {displayColumns.map((col) => (
                <th
                  key={col.name}
                  style={{
                    padding: '10px 12px',
                    textAlign: 'left',
                    fontWeight: 'bold',
                    color: '#475569',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    borderBottom: '2px solid #e2e8f0',
                    whiteSpace: 'nowrap',
                    position: 'sticky',
                    top: 0,
                    backgroundColor: '#f1f5f9',
                  }}
                >
                  {col.displayName}
                  {col.kind && (
                    <span style={{ marginLeft: '6px', fontSize: '9px', color: '#94a3b8', fontFamily: 'monospace' }}>
                      {col.kind === 'Number' ? '#' : col.kind === 'Str' ? 's' : col.kind === 'Ref' ? '@' : col.kind === 'Bool' ? '?' : col.kind.slice(0, 2)}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => {
              return (
                <tr
                  key={`row-${rowIndex}`}
                  onClick={() => onRowClick?.(row)}
                  style={{
                    borderBottom: '1px solid #f1f5f9',
                    cursor: onRowClick ? 'pointer' : 'default',
                    transition: 'background-color 0.15s',
                  }}
                  onMouseEnter={(e) => { if (onRowClick) e.currentTarget.style.backgroundColor = '#f8fafc'; }}
                  onMouseLeave={(e) => { if (onRowClick) e.currentTarget.style.backgroundColor = 'transparent'; }}
                >
                  {displayColumns.map((col) => {
                    let cellValue: any = null;
                    try {
                      cellValue = row.get(col.name);
                    } catch {
                      // Column not in this row
                    }

                    const formatted = formatCellValue(cellValue);
                    const cellStyle = getValueStyle(cellValue);

                    return (
                      <td
                        key={`${rowIndex}-${col.name}`}
                        style={{
                          padding: '10px 12px',
                          maxWidth: '250px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          ...cellStyle,
                        }}
                        title={formatted.length > 30 ? formatted : undefined}
                      >
                        {formatted}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div style={{ backgroundColor: '#f8fafc', borderTop: '1px solid #e2e8f0', padding: '8px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#94a3b8' }}>
        <span>Grid 数据预览</span>
        <span>点击行查看详情</span>
      </div>
    </div>
  );
};

// ============================================================
// Mock Table Component (for demo/testing)
// ============================================================

interface MockTableProps {
  title: string;
  subtitle?: string;
}

const MockTable = ({ title, subtitle }: MockTableProps) => {
  const mockData = [
    { id: 'AHU-01', name: 'AHU-01', floor: '12F', type: 'AHU', status: 'online', temp: 22.5, flow: 1500 },
    { id: 'AHU-02', name: 'AHU-02', floor: '11F', type: 'AHU', status: 'online', temp: 23.1, flow: 1450 },
    { id: 'VAV-12-01', name: 'VAV-12-01', floor: '12F', type: 'VAV', status: 'alarm', temp: 24.0, flow: 180 },
    { id: 'VAV-12-02', name: 'VAV-12-02', floor: '12F', type: 'VAV', status: 'online', temp: 22.8, flow: 200 },
    { id: 'VAV-11-01', name: 'VAV-11-01', floor: '11F', type: 'VAV', status: 'offline', temp: 0, flow: 0 },
  ];

  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: '设备名称' },
    { key: 'floor', label: '楼层' },
    { key: 'type', label: '类型' },
    { key: 'status', label: '状态' },
    { key: 'temp', label: '温度 (°C)', isNumber: true },
    { key: 'flow', label: '风量 (CFM)', isNumber: true },
  ];

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'online': return { color: '#10b981', fontWeight: 'bold' };
      case 'alarm': return { color: '#f59e0b', fontWeight: 'bold' };
      case 'offline': return { color: '#94a3b8' };
      default: return { color: '#64748b' };
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'online': return '● 在线';
      case 'alarm': return '▲ 告警';
      case 'offline': return '○ 离线';
      default: return status;
    }
  };

  return (
    <div style={{ marginTop: '12px', backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
      <div style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={16} style={{ color: '#2563eb' }} />
            <span style={{ fontWeight: 'bold', color: '#1e293b', fontSize: '14px' }}>{title}</span>
          </div>
          {subtitle && <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', marginLeft: '24px' }}>{subtitle}</div>}
        </div>
        <span style={{ fontSize: '10px', color: '#8b5cf6', backgroundColor: '#f5f3ff', padding: '2px 6px', borderRadius: '4px' }}>模拟数据</span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f1f5f9' }}>
              {columns.map((col) => (
                <th key={col.key} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 'bold', color: '#475569', fontSize: '11px', textTransform: 'uppercase', borderBottom: '2px solid #e2e8f0' }}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mockData.map((row) => (
              <tr key={row.id} style={{ borderBottom: '1px solid #f1f5f9' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#f8fafc'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}>
                {columns.map((col) => {
                  const value = row[col.key as keyof typeof row];
                  const isNumber = col.isNumber;
                  const isStatus = col.key === 'status';
                  return (
                    <td key={col.key} style={{ padding: '10px 12px', ...(isNumber ? { fontFamily: 'monospace', color: '#2563eb' } : {}), ...(isStatus ? getStatusStyle(String(value)) : { color: '#334155' }) }}>
                      {isStatus ? getStatusLabel(String(value)) : String(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ backgroundColor: '#f8fafc', borderTop: '1px solid #e2e8f0', padding: '8px 16px', fontSize: '10px', color: '#94a3b8' }}>
        模拟数据预览 - 连接 Haystack 后显示实际数据
      </div>
    </div>
  );
};

// ============================================================
// Main App Component
// ============================================================

function App() {
  // Connection & System state
  const [, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    fantom: 'Connected',
    python: 'Standby',
    folio: 'OK',
    llm: 'enabled',
  });
  // LLM status - derived from systemStatus.llm
  const llmStatus = systemStatus.llm === 'enabled' ? 'enabled' : 'disabled';

  // Chat state
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  // Sidebar state with responsive initial value
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Diagnostic state
  const [diagnosticData, setDiagnosticData] = useState<DiagnosticDetails | null>(null);

  // HMI Preview state
  const [hmiLayout, setHmiLayout] = useState<HmiLayout | null>(null);

  // Test connection on mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        setIsTyping(true);
        await getAbout();
        setConnectionStatus('connected');
        setSystemStatus({
          fantom: 'Connected',
          python: 'Standby',
          folio: 'OK',
        });
      } catch (error) {
        setConnectionStatus('disconnected');
        setSystemStatus({
          fantom: 'Disconnected',
          python: 'Standby',
          folio: 'Error',
        });
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: 'assistant',
            type: 'text',
            content: `连接失败: ${error instanceof Error ? error.message : 'Unknown error'}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      } finally {
        setIsTyping(false);
      }
    };

    testConnection();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTop = messagesEndRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Responsive sidebar: update state when window crosses breakpoint
  useEffect(() => {
    const handleResize = () => {
      const isDesktop = window.innerWidth >= 768;
      setSidebarOpen(isDesktop);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // ============================================================
  // Agent Workflow Execution (模拟后端 agent_workflow.route)
  // ============================================================

  interface LLMIntent {
    keywords: string[];
    intent: string;
    action: string;
  }

  interface EngineResult {
    status: 'ok' | 'stub' | 'error';
    message: string;
    data?: Record<string, unknown>;
    confidence?: number;
  }

  const executeAgentWorkflow = async (intent: LLMIntent, originalQuery: string) => {
    // 步骤 1: 显示 LLM 意图解析结果
    await new Promise((resolve) => setTimeout(resolve, 600));

    const llmResponse: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      type: 'text',
      content: `**LLM 意图解析**\n\n识别意图: \`${intent.intent}\`\n路由动作: \`${intent.action}\`\n置信度: \`0.95\`\n\n> ${getIntentDescription(intent.intent)}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      llmConfidence: 0.95,
      llmThought: `关键词匹配成功，路由到 ${intent.action} 引擎`,
      llmEnabled: true,
      verified: true,
    };
    setMessages((prev) => [...prev, llmResponse]);

    // 步骤 2: 显示引擎路由信息
    await new Promise((resolve) => setTimeout(resolve, 400));

    const routeMessage: Message = {
      id: Date.now().toString() + '-route',
      role: 'assistant',
      type: 'text',
      content: `**AgentWorkflow 路由**\n\n调用引擎: \`${getEngineName(intent.action)}\`\n执行动作: \`${intent.action}\``,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      verified: true,
    };
    setMessages((prev) => [...prev, routeMessage]);

    // 步骤 3: 执行引擎并返回结果
    await new Promise((resolve) => setTimeout(resolve, 800));

    const engineResult = await executeEngine(intent.action, originalQuery);

    if (engineResult.status === 'ok') {
      // 根据不同引擎返回不同类型的消息
      const resultMessage = getEngineResultMessage(intent.action, engineResult, originalQuery);
      setMessages((prev) => [...prev, resultMessage]);

      // 如果有额外数据（如诊断详情、HMI布局等），设置状态
      if (engineResult.data) {
        if ('diagnosticDetails' in engineResult.data) {
          setDiagnosticData(engineResult.data.diagnosticDetails as DiagnosticDetails);
        }
        if ('hmiLayout' in engineResult.data) {
          setHmiLayout(engineResult.data.hmiLayout as HmiLayout);
        }
      }
    } else {
      // 引擎执行失败
      const errorMessage: Message = {
        id: Date.now().toString() + '-error',
        role: 'assistant',
        type: 'text',
        content: `**引擎执行错误**\n\n${engineResult.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        verified: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const getEngineName = (action: string): string => {
    const engineMap: Record<string, string> = {
      'diagnose': 'FddEngine',
      'optimize': 'EnergyOptEngine',
      'inspect': 'InspectEngine',
      'hmi': 'HmiEngine',
      'report': 'ReportEngine',
      'query': 'QueryEngine',
      'tag': 'TaggingEngine',
    };
    return engineMap[action] || 'UnknownEngine';
  };

  const executeEngine = async (action: string, query: string): Promise<EngineResult> => {
    // 模拟各个引擎的执行
    switch (action) {
      case 'diagnose':
        return {
          status: 'ok',
          message: '已完成故障诊断分析',
          confidence: 0.92,
          data: {
            diagnosticDetails: {
              step1: '语义解析: Scope=Floor3, Type=Temp',
              step2: 'Folio 查询',
              step3: 'hxPy 推理: 检测到 VAV-12 末端阀门卡死',
              rootCause: '阀门机械故障导致冷量无法有效输送',
              commandState: '风阀开度: 100%',
              sensorFeedback: '气流值: 0.05 L/s',
            },
          },
        };

      case 'optimize':
        return {
          status: 'ok',
          message: '能源优化参数已计算',
          confidence: 0.88,
          data: {
            originalSetpoint: 18,
            recommendedSetpoint: 16,
            estimatedSavings: '12%',
            reasoning: '当前室外温度较低，可适当降低送风温度设定值以节约能源',
          },
        };

      case 'inspect':
        return {
          status: 'ok',
          message: '传感器健康检查完成',
          confidence: 0.95,
          data: {
            totalSensors: 24,
            healthy: 21,
            warning: 2,
            critical: 1,
            issues: [
              { sensor: 'T-AHU-01-01', issue: '数据漂移', health: 65 },
              { sensor: 'T-AHU-02-03', issue: '通信超时', health: 42 },
            ],
          },
        };

      case 'hmi':
        return {
          status: 'ok',
          message: 'HMI 画面布局已生成',
          confidence: 0.90,
          data: {
            hmiLayout: {
              device: 'AHU-01',
              binding: 'Auto-binding via equipRef',
              components: [
                { type: 'gauge', id: 'supplyAirTemp', label: '送风温度' },
                { type: 'number', id: 'returnAirTemp', label: '回风温度' },
                { type: 'gauge', id: 'valvePosition', label: '阀门开度' },
                { type: 'trend', id: 'energyTrend', label: '能耗趋势' },
              ],
            },
          },
        };

      case 'report':
        return {
          status: 'ok',
          message: '运维日报已生成',
          confidence: 0.85,
          data: {
            date: new Date().toISOString().split('T')[0],
            totalAlarms: 3,
            resolved: 2,
            pending: 1,
            energyConsumption: '12,450 kWh',
            summary: '今日系统运行平稳，AHU-01 出现 1 次过滤网堵塞报警，已派单处理。',
          },
        };

      case 'query':
        return {
          status: 'ok',
          message: '查询已执行',
          confidence: 1.0,
          data: {
            query,
            results: '模拟查询结果...',
          },
        };

      default:
        return {
          status: 'error',
          message: `未知动作: ${action}`,
        };
    }
  };

  const getEngineResultMessage = (action: string, result: EngineResult, originalQuery: string): Message => {
    const baseProps = {
      id: Date.now().toString() + '-result',
      role: 'assistant' as const,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      verified: true,
      llmEnabled: true,
    };

    switch (action) {
      case 'diagnose':
        return {
          ...baseProps,
          type: 'diagnosis' as const,
          content: `${result.message}\n\n根因分析: ${(result.data?.diagnosticDetails as DiagnosticDetails)?.rootCause || '未知'}`,
        };

      case 'optimize':
        return {
          ...baseProps,
          type: 'text' as const,
          content: `**能源优化建议**\n\n当前设定值: \`${result.data?.originalSetpoint}°C\`\n推荐设定值: \`${result.data?.recommendedSetpoint}°C\`\n预计节能: \`${result.data?.estimatedSavings}\`\n\n> ${result.data?.reasoning}`,
          llmConfidence: result.confidence,
        };

      case 'inspect':
        const inspectData = result.data as { totalSensors: number; healthy: number; warning: number; critical: number; issues: Array<{ sensor: string; issue: string; health: number }> };
        return {
          ...baseProps,
          type: 'text' as const,
          content: `**传感器巡检报告**\n\n总计: \`${inspectData.totalSensors}\` | 健康: \`${inspectData.healthy}\` | 警告: \`${inspectData.warning}\` | 严重: \`${inspectData.critical}\`\n\n**异常列表:**\n${inspectData.issues.map(i => `- \`${i.sensor}\`: ${i.issue} (健康度: ${i.health}%)`).join('\n')}`,
          llmConfidence: result.confidence,
        };

      case 'hmi':
        const hmiData = result.data as { hmiLayout?: { device?: string; components?: unknown[] } };
        return {
          ...baseProps,
          type: 'hmi' as const,
          content: `${result.message}\n\n已为 ${hmiData.hmiLayout?.device || '设备'} 生成包含 ${hmiData.hmiLayout?.components?.length || 0} 个组件的监控画面。点击"确认发布"将布局发送到 FIN Graphics Builder。`,
        };

      case 'report':
        const reportData = result.data as { date: string; totalAlarms: number; resolved: number; pending: number; energyConsumption: string; summary: string };
        return {
          ...baseProps,
          type: 'text' as const,
          content: `**运维日报** (${reportData.date})\n\n报警情况: 总计 \`${reportData.totalAlarms}\` (已处理 \`${reportData.resolved}\` | 待处理 \`${reportData.pending}\`)\n能耗统计: \`${reportData.energyConsumption}\`\n\n**总结:**\n${reportData.summary}`,
          llmConfidence: result.confidence,
        };

      case 'query':
        return {
          ...baseProps,
          type: 'text' as const,
          content: `**查询结果**\n\n执行查询: \`${originalQuery}\`\n\n${result.message}\n> 前端模拟模式 - 连接实际 Haystack 后将显示真实数据`,
        };

      default:
        return {
          ...baseProps,
          type: 'text' as const,
          content: result.message,
        };
    }
  };

  // Handle send message
  const handleSend = async (content: string) => {
    if (!content.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      type: 'text',
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Activate Python brain
    setSystemStatus((prev) => ({ ...prev, python: 'Active' }));
    setIsTyping(true);
    setInputValue('');

    try {
      const query = content.toLowerCase();

      // LLM Intent Parsing - 模拟后端 LLM 解析响应
      const llmIntents = [
        { keywords: ['诊断', '故障', '报警', 'diagnos', 'alarm', 'fault'], intent: 'ACTION_DIAGNOSIS', action: 'diagnose' },
        { keywords: ['优化', '节能', '设定值', 'optim', 'energy', 'setpoint'], intent: 'ACTION_OPTIMIZE', action: 'optimize' },
        { keywords: ['巡检', '检查', '传感器', 'inspect', 'health', 'sensor'], intent: 'ACTION_INSPECT', action: 'inspect' },
        { keywords: ['hmi', '界面', '画面', 'layout', 'graphic'], intent: 'ACTION_HMI', action: 'hmi' },
        { keywords: ['报告', '日报', '总结', 'report', 'summar'], intent: 'ACTION_REPORT', action: 'report' },
        { keywords: ['查询', '数据', '趋势', 'query', 'data', 'trend'], intent: 'ACTION_QUERY', action: 'query' },
      ];

      let matchedIntent: typeof llmIntents[0] | null = null;
      for (const intent of llmIntents) {
        if (intent.keywords.some(k => query.includes(k))) {
          matchedIntent = intent;
          break;
        }
      }

      if (matchedIntent) {
        await executeAgentWorkflow(matchedIntent, content);
      } else {
        // Default: try to query Haystack
        await new Promise((resolve) => setTimeout(resolve, 800));

        let responseMessage: Message;
        try {
          const result = await readEntities(content, 50);

          console.log('[handleSend] Raw result:', result);
          console.log('[handleSend] Result type:', typeof result);
          console.log('[handleSend] Result keys:', result ? Object.keys(result) : 'null');

          if (result) {
            // Try to get row count
            let rowCount = 0;
            try {
              rowCount = [...result].length;
            } catch {
              try {
                rowCount = (result as any).rows?.length || 0;
              } catch {
                // Use length property if available
                rowCount = (result as any).length || 0;
              }
            }

            console.log('[handleSend] Row count:', rowCount);

            // Check if result has grid structure (cols or rows array)
            const hasCols = (result as any).cols && Array.isArray((result as any).cols);
            const hasRows = (result as any).rows && Array.isArray((result as any).rows);
            const hasGridStructure = hasCols || hasRows || rowCount > 0;

            console.log('[handleSend] hasCols:', hasCols, 'hasRows:', hasRows, 'hasGridStructure:', hasGridStructure);

            responseMessage = {
              id: Date.now().toString(),
              role: 'assistant',
              type: 'grid',
              content: `查询到 ${rowCount} 条记录`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              verified: true,
              gridData: result,
              gridTitle: `"${content}" 查询结果`,
            };
          } else {
            responseMessage = {
              id: Date.now().toString(),
              role: 'assistant',
              type: 'text',
              content: '查询未返回结果，请尝试其他查询条件。',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            };
          }
        } catch (error) {
          console.log('[handleSend] Error:', error);
          responseMessage = {
            id: Date.now().toString(),
            role: 'assistant',
            type: 'text',
            content: `查询失败: ${error instanceof Error ? error.message : '未知错误'}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
        }
        setMessages((prev) => [...prev, responseMessage]);
      }
    } finally {
      setIsTyping(false);
      setSystemStatus((prev) => ({ ...prev, python: 'Standby' }));
    }
  };

  const handleExecuteDiagnostic = async (action: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      type: 'text',
      content: `执行操作: ${action}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMessage]);

    await new Promise((resolve) => setTimeout(resolve, 1000));

    const agentMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      type: 'text',
      content: `操作已执行\n\n正在通过 AXON 执行: ${action}\n\n操作确认：工程师 #02 已收到`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, agentMessage]);

    setDiagnosticData(null);
  };

  const handleConfirmHmi = async () => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      type: 'text',
      content: '确认发布 HMI 布局到 FIN Graphics Builder',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMessage]);

    await new Promise((resolve) => setTimeout(resolve, 1000));

    const agentMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      type: 'text',
      content: `HMI 布局已发布\n\n布局 ID: layout_hmi_ahu01\n\n发布到以下页面：\n• AHU 监控仪表盘\n• VAV 末端控制面板\n• 趋势分析图`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, agentMessage]);

    setHmiLayout(null);
  };

  const handleClearChat = () => {
    setMessages(INITIAL_MESSAGES);
    setDiagnosticData(null);
    setHmiLayout(null);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(inputValue);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getIntentDescription = (intent: string): string => {
    const descriptions: Record<string, string> = {
      'ACTION_DIAGNOSIS': '用于诊断故障、分析报警原因、查找运行异常的根因',
      'ACTION_OPTIMIZE': '用于能源优化、设定值调整、节能策略',
      'ACTION_INSPECT': '用于传感器巡检、健康检查、设备状态查询',
      'ACTION_HMI': '用于生成、创建、布置 HMI 监控画面或图形界面',
      'ACTION_REPORT': '用于生成日报、运维总结、操作摘要',
      'ACTION_QUERY': '用于查询实时数据、历史趋势或设备状态',
    };
    return descriptions[intent] || '未知意图';
  };

  const suggestions = [
    'site',
    'equip',
    'point',
    '诊断一下AHU-01的送风温度异常',
    '优化12楼空调设定值',
    '检查所有温度传感器状态',
    '为当前风柜生成监控画面预览',
    '清空当前对话环境',
  ];

  // ============================================================
  // Render
  // ============================================================

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#020617', color: '#e2e8f0', overflow: 'hidden', fontFamily: 'sans-serif' }}>
      {/* Desktop Sidebar */}
      <aside
        style={{
          position: 'fixed', inset: 0, left: 0, zIndex: 50, width: '288px',
          backgroundColor: '#0f172a', borderRight: '1px solid #1e293b',
          display: 'flex', flexDirection: 'column', transition: 'transform 0.3s',
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)'
        }}
      >
        <div style={{ padding: '24px', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '32px', height: '32px', backgroundColor: '#2563eb', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Cpu size={20} style={{ color: 'white' }} />
            </div>
            <span style={{ fontWeight: 'bold', letterSpacing: '0.05em', color: 'white', textTransform: 'uppercase', fontSize: '14px' }}>EPC Monitoring</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            style={{ display: 'none', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', padding: '4px' }}
            className="md-block"
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Status Group 1 */}
          <section>
            <h3 style={{ fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={12} /> 系统状态
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: 'rgba(30, 41, 59, 0.3)', padding: '12px', borderRadius: '12px', border: '1px solid #1e293b' }}>
              <StatusItem label="Fantom / AXON" value={systemStatus.fantom} status={systemStatus.fantom === 'Connected' ? 'online' : 'offline'} />
              <StatusItem label="Python / hxPy" value={systemStatus.python} status={systemStatus.python === 'Active' ? 'online' : 'idle'} />
              <StatusItem label="LLM 解析" value={llmStatus ? '已启用' : '未启用'} status={llmStatus ? 'online' : 'offline'} />
              <StatusItem label="项目" value="CBD Central" />
            </div>
          </section>

          {/* Status Group 2 */}
          <section>
            <h3 style={{ fontSize: '10px', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={12} /> 数据资产统计
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>Haystack Entities</span>
                <span style={{ fontSize: '18px', fontFamily: 'monospace', color: '#60a5fa' }}>14,203</span>
              </div>
              <div style={{ width: '100%', backgroundColor: '#1e293b', height: '6px', borderRadius: '999px', overflow: 'hidden' }}>
                <div style={{ backgroundColor: '#3b82f6', height: '100%', width: '85%', borderRadius: '999px', boxShadow: '0 0 8px rgba(59,130,246,0.5)' }}></div>
              </div>
            </div>
          </section>

          {/* Security & Audit */}
          <section style={{ paddingTop: '16px', borderTop: '1px solid #1e293b' }}>
            <div style={{ padding: '12px', backgroundColor: 'rgba(30, 64, 175, 0.2)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#60a5fa', marginBottom: '8px' }}>
                <ShieldCheck size={14} />
                <span style={{ fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}>Security Guard</span>
              </div>
              <p style={{ fontSize: '10px', color: '#93c5fd', lineHeight: '1.5', fontStyle: 'italic' }}>
                API 写操作受控模式。任何写操作均需二次签名校验。
              </p>
            </div>
          </section>
        </div>

        <div style={{ padding: '16px', borderTop: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button
            onClick={handleClearChat}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', borderRadius: '8px', fontSize: '14px', transition: 'all 0.2s', cursor: 'pointer' }}
          >
            <Trash2 size={16} /> <span>清空会话</span>
          </button>
          <button style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', borderRadius: '8px', fontSize: '14px', transition: 'all 0.2s', cursor: 'pointer' }}>
            <Settings size={16} /> <span>系统设置</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        backgroundColor: 'white',
        borderRadius: 0,
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.1)',
        overflow: 'hidden',
        marginLeft: sidebarOpen && window.innerWidth >= 768 ? '288px' : '0',
        transition: 'margin-left 0.3s'
      }}>
        {/* Header */}
        <header style={{ height: '64px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', padding: '0 24px', justifyContent: 'space-between', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button
              onClick={() => setSidebarOpen(true)}
              style={{ display: 'none', color: '#475569', backgroundColor: 'transparent', border: 'none', padding: '4px' }}
              className="md-block"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 style={{ color: '#0f172a', fontWeight: 'bold', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                运维自动化 AI 助手
                <span style={{ padding: '4px 8px 2px', backgroundColor: '#f1f5f9', color: '#64748b', fontSize: '10px', borderRadius: '4px', textTransform: 'uppercase' }}>
                  v2.5 Professional
                </span>
              </h1>
              <div style={{ fontSize: '10px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
                已同步 1,420 个点位到 AXON 缓冲区
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'none', gap: '4px' }} className="sm-flex">
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', cursor: 'pointer', transition: 'background-color 0.2s' }}>
                <ExternalLink size={16} />
              </div>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', cursor: 'pointer', transition: 'background-color 0.2s' }}>
                <Plus size={16} />
              </div>
            </div>
          </div>
        </header>

        {/* Message List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 32px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
            >
              <div style={{ maxWidth: msg.role === 'user' ? '85%' : '70%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', padding: '0 4px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {msg.role === 'user' ? 'Operator' : 'Haxall Agent'}
                  </span>
                  <span style={{ fontSize: '10px', color: '#cbd5e1', fontFamily: 'monospace' }}>{msg.timestamp}</span>
                </div>

                <div
                  style={{
                    position: 'relative', padding: '16px', borderRadius: '16px', fontSize: '14px', lineHeight: '1.5', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    backgroundColor: msg.role === 'user' ? '#0f172a' : 'white',
                    color: msg.role === 'user' ? 'white' : '#1e293b',
                    border: msg.role === 'user' ? '1px solid #1e293b' : '1px solid #e2e8f0',
                    borderTopLeftRadius: msg.role === 'user' ? '0' : '16px',
                    borderTopRightRadius: msg.role === 'user' ? '16px' : '0',
                  }}
                >
                  {/* Render Specialized Components */}
                  {msg.type === 'diagnosis' && <DiagnosisCardInline data={diagnosticData ?? undefined} onExecute={handleExecuteDiagnostic} />}
                  {msg.type === 'hmi' && <HmiPreviewCard layout={hmiLayout ?? undefined} onConfirm={handleConfirmHmi} />}
                  {msg.type === 'tagging' && <AutoTaggingCard />}
                  {msg.type === 'grid' && msg.gridData && (
                    <GridTable
                      grid={msg.gridData}
                      title={msg.gridTitle || '查询结果'}
                      subtitle={msg.content}
                      onRowClick={(row) => {
                        console.log('Row clicked:', row);
                      }}
                    />
                  )}
                  {/* Mock table for demo when (msg as any).mockTable is true */}
                  {(msg as any).mockTable && (
                    <MockTable
                      title={msg.gridTitle || '查询结果'}
                      subtitle={msg.content}
                    />
                  )}

                  {/* Default Text Content */}
                  {msg.content && msg.type !== 'diagnosis' && msg.type !== 'tagging' && (
                    <div
                      style={{ fontSize: '14px', lineHeight: '1.5' }}
                      dangerouslySetInnerHTML={{
                        __html: msg.content
                          .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #2563eb;">$1</strong>')
                          .replace(/`(.*?)`/g, '<code style="background-color: #f1f5f9; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-family: monospace;">$1</code>')
                          .replace(/> (.*)/g, '<em style="color: #64748b;">$1</em>')
                          .replace(/\n/g, '<br />')
                      }}
                    />
                  )}

                  {/* Actions (Floating on Hover) */}
                  {msg.content && (
                    <div
                      style={{
                        position: 'absolute', top: 0, left: msg.role === 'user' ? '-40px' : 'auto', right: msg.role === 'user' ? 'auto' : '-40px',
                        opacity: 0, transition: 'opacity 0.2s', display: 'flex', flexDirection: 'column', gap: '4px', padding: '4px'
                      }}
                      onMouseOver={(e) => { e.currentTarget.style.opacity = '1'; }}
                      onMouseOut={(e) => { e.currentTarget.style.opacity = '0'; }}
                    >
                      <button
                        onClick={() => copyToClipboard(msg.content)}
                        style={{ padding: '6px', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', borderRadius: '4px', cursor: 'pointer', transition: 'color 0.2s' }}
                      >
                        <Copy size={14} />
                      </button>
                    </div>
                  )}

                  {/* Verified Footnote with LLM Info */}
                  {msg.role === 'assistant' && msg.verified && (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '9px', color: '#94a3b8', fontFamily: 'monospace' }}>
                        <Check size={10} style={{ color: '#10b981' }} /> Verified by Haxall
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {/* LLM Badge */}
                        {msg.llmEnabled !== false && (
                          <div style={{ fontSize: '9px', color: '#7c3aed', fontWeight: 'bold', letterSpacing: '0.1em', backgroundColor: '#f5f3ff', padding: '2px 6px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Sparkles size={10} /> LLM
                          </div>
                        )}
                        {/* Confidence Score */}
                        {msg.llmConfidence !== undefined && (
                          <div style={{ fontSize: '9px', color: '#059669', fontWeight: 'bold', backgroundColor: '#ecfdf5', padding: '2px 6px', borderRadius: '4px' }}>
                            {Math.round(msg.llmConfidence * 100)}% 置信
                          </div>
                        )}
                        {/* Framework Badge */}
                        <div style={{ fontSize: '9px', color: '#2563eb', fontWeight: 'bold', letterSpacing: '0.1em', backgroundColor: '#eff6ff', padding: '2px 4px', borderRadius: '4px' }}>
                          AXON_FRW
                        </div>
                      </div>
                    </div>
                  )}
                  {/* LLM Thought Process */}
                  {msg.llmThought && (
                    <div style={{ marginTop: '8px', padding: '8px 12px', backgroundColor: '#fefce8', border: '1px solid #fde047', borderRadius: '8px', fontSize: '11px', color: '#854d0e', fontStyle: 'italic' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', fontWeight: 'bold' }}>
                        <Sparkles size={10} /> AI 思考过程
                      </div>
                      {msg.llmThought}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', padding: '16px', borderRadius: '16px', borderTopLeftRadius: '0' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#cbd5e1', animation: 'bounce 1s infinite' }}></div>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#cbd5e1', animation: 'bounce 1s infinite', animationDelay: '0.2s' }}></div>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#cbd5e1', animation: 'bounce 1s infinite', animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{ padding: '16px 24px', backgroundColor: 'white', borderTop: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Suggestions */}
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
            {suggestions.map((text, i) => (
              <button
                key={i}
                onClick={() => {
                  setInputValue(text);
                  inputRef.current?.focus();
                }}
                style={{ whiteSpace: 'nowrap', padding: '6px 12px', backgroundColor: '#f8fafc', color: '#475569', border: '1px solid #e2e8f0', borderRadius: '999px', fontSize: '12px', transition: 'all 0.2s', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Zap size={10} /> {text}
              </button>
            ))}
          </div>

          <div style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <div style={{ position: 'absolute', inset: '-2px', background: 'linear-gradient(to right, #2563eb, #4f46e5)', borderRadius: '16px', filter: 'blur(6px)', opacity: '0.1', transition: 'opacity 0.2s' }}></div>
            <div style={{ position: 'relative', backgroundColor: '#f8fafc', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="键入运维问题、HMI 指令或点位字符串..."
                rows={1}
                style={{ width: '100%', backgroundColor: 'transparent', border: 'none', color: '#1e2937', fontSize: '14px', minHeight: '44px', maxHeight: '200px', resize: 'none', padding: '12px 8px', fontFamily: 'inherit' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 8px 4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <button style={{ padding: '8px', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', borderRadius: '8px', cursor: 'pointer', transition: 'color 0.2s' }}>
                    <Paperclip size={18} />
                  </button>
                  <button style={{ padding: '8px', color: '#94a3b8', backgroundColor: 'transparent', border: 'none', borderRadius: '8px', cursor: 'pointer', transition: 'color 0.2s' }}>
                    <Zap size={18} />
                  </button>
                  <div style={{ width: '1px', height: '16px', backgroundColor: '#e2e8f0', margin: '0 4px' }}></div>
                  <span style={{ fontSize: '10px', color: '#94a3b8', padding: '0 4px', fontFamily: 'monospace', textTransform: 'uppercase' }}>hxPy mode</span>
                </div>
                <button
                  onClick={() => handleSend(inputValue)}
                  disabled={!inputValue.trim() || isTyping}
                  style={{
                    padding: '8px 16px', borderRadius: '12px', border: 'none', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s',
                    backgroundColor: inputValue.trim() ? '#2563eb' : '#e2e8f0',
                    color: 'white', opacity: inputValue.trim() ? 1 : 0.5,
                    boxShadow: inputValue.trim() ? '0 4px 6px rgba(37, 99, 235, 0.2)' : 'none'
                  }}
                >
                  <span style={{ fontSize: '12px', fontWeight: 'bold', display: 'none' }} className="sm-block">发送指令</span>
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>

          <p style={{ fontSize: '10px', textAlign: 'center', color: '#94a3b8', fontWeight: '500' }}>
            提示：Shift + Enter 换行。所有控制操作将通过审核策略同步至现场控制器。
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
