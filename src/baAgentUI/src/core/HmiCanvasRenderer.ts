// ============================================================
// HmiCanvasRenderer — Grid-to-SVG coordinate mapping
// ============================================================

import type { HmiWidget, HmiPage, SvgWidgetProps } from '../types';
import type { ComponentType } from 'react';
import { SmartWidgetLibrary } from '../components/HmiCanvas/widgets';

interface CanvasSize {
  width: number;
  height: number;
}

const CELL_PADDING = 4;

export class HmiCanvasRenderer {
  /**
   * Map a widget's grid position to SVG pixel coordinates.
   */
  static mapToSvg(
    widget: HmiWidget,
    page: HmiPage,
    canvasSize: CanvasSize
  ): { x: number; y: number; width: number; height: number } {
    const cellW = canvasSize.width / page.grid_columns;
    const cellH = canvasSize.height / page.grid_rows;

    return {
      x: (widget.col - 1) * cellW + CELL_PADDING,
      y: (widget.row - 1) * cellH + CELL_PADDING,
      width: widget.col_span * cellW - CELL_PADDING * 2,
      height: widget.row_span * cellH - CELL_PADDING * 2,
    };
  }

  /**
   * Resolve widget type string to the corresponding SVG React component.
   */
  static resolveWidget(
    widgetType: HmiWidget['widget_type']
  ): ComponentType<SvgWidgetProps> {
    return SmartWidgetLibrary[widgetType] ?? SmartWidgetLibrary.status;
  }
}
