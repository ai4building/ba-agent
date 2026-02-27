// ============================================================
// SmartWidgetLibrary — Widget type → SVG component registry
// ============================================================

import type { ComponentType } from 'react';
import type { SvgWidgetProps, HmiWidget } from '../../../types';
import { GaugeWidget } from './GaugeWidget';
import { TrendWidget } from './TrendWidget';
import { StatusWidget } from './StatusWidget';
import { SetpointWidget } from './SetpointWidget';
import { AlarmWidget } from './AlarmWidget';

export const SmartWidgetLibrary: Record<
  HmiWidget['widget_type'],
  ComponentType<SvgWidgetProps>
> = {
  gauge: GaugeWidget,
  trend: TrendWidget,
  status: StatusWidget,
  setpoint: SetpointWidget,
  alarm: AlarmWidget,
};
