// ============================================================
// Unit Conversion Utilities
// Using haystack-units for accurate conversions
// ============================================================

import {
  celsius,
  fahrenheit,
  kelvin,
  pascal,
  kilopascal,
  bar,
  poundsPerSquareInch,
  cubicMetersPerSecond,
  cubicFeetPerMinute,
  litersPerSecond,
  kilowatt,
  watt,
  cubicMeter,
  liter,
  gallon,
} from 'haystack-units';
import { HNum } from 'haystack-core';

// ============================================================
// Temperature Conversions
// ============================================================

/**
 * Convert temperature between units
 * @param value - Temperature value
 * @param fromUnit - Source unit (°C, °F, K)
 * @param toUnit - Target unit (°C, °F, K)
 * @returns Converted value
 */
export function convertTemperature(
  value: number,
  fromUnit: string,
  toUnit: string
): number {
  const num = HNum.make(value, fromUnit);
  const targetUnit = getTemperatureUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.value;
}

/**
 * Convert Celsius to Fahrenheit
 */
export function celsiusToFahrenheit(celsiusVal: number): number {
  return convertTemperature(celsiusVal, '°C', '°F');
}

/**
 * Convert Fahrenheit to Celsius
 */
export function fahrenheitToCelsius(fahrenheitVal: number): number {
  return convertTemperature(fahrenheitVal, '°F', '°C');
}

/**
 * Format temperature with unit
 */
export function formatTemperature(value: number, unit: string = '°C'): string {
  return `${value.toFixed(1)}°${unit === '°C' ? 'C' : unit === '°F' ? 'F' : 'K'}`;
}

// ============================================================
// Pressure Conversions
// ============================================================

/**
 * Convert pressure between units
 * @param value - Pressure value
 * @param fromUnit - Source unit (Pa, kPa, bar, psi)
 * @param toUnit - Target unit
 */
export function convertPressure(
  value: number,
  fromUnit: string,
  toUnit: string
): number {
  const num = HNum.make(value, fromUnit);
  const targetUnit = getPressureUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.value;
}

/**
 * Convert Pascal to Bar
 */
export function pascalToBar(pascalVal: number): number {
  return convertPressure(pascalVal, 'Pa', 'bar');
}

/**
 * Convert PSI to Bar
 */
export function psiToBar(psi: number): number {
  return convertPressure(psi, 'psi', 'bar');
}

/**
 * Format pressure with unit
 */
export function formatPressure(value: number, unit: string = 'kPa'): string {
  return `${value.toFixed(2)} ${unit}`;
}

// ============================================================
// Flow Rate Conversions
// ============================================================

/**
 * Convert flow rate between units
 * @param value - Flow rate value
 * @param fromUnit - Source unit (m³/s, CFM, L/s)
 * @param toUnit - Target unit
 */
export function convertFlow(
  value: number,
  fromUnit: string,
  toUnit: string
): number {
  const num = HNum.make(value, fromUnit);
  const targetUnit = getFlowUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.value;
}

/**
 * Convert CFM to m³/s
 */
export function cfmToCubicMeterPerSecond(cfm: number): number {
  return convertFlow(cfm, 'CFM', 'm³/s');
}

/**
 * Format flow rate with unit
 */
export function formatFlow(value: number, unit: string = 'm³/s'): string {
  if (unit === 'CFM') {
    return `${value.toFixed(0)} CFM`;
  }
  return `${value.toFixed(2)} ${unit}`;
}

// ============================================================
// Power/Energy Conversions
// ============================================================

/**
 * Convert power between units
 * @param value - Power value
 * @param fromUnit - Source unit (kW, BTU/h)
 * @param toUnit - Target unit
 */
export function convertPower(
  value: number,
  fromUnit: string,
  toUnit: string
): number {
  const num = HNum.make(value, fromUnit);
  const targetUnit = getPowerUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.value;
}

/**
 * Convert kW to BTU/h
 */
export function kilowattToBtuPerHour(kw: number): number {
  return convertPower(kw, 'kW', 'Btu/h');
}

/**
 * Convert BTU/h to kW
 */
export function btuPerHourToKilowatt(btuh: number): number {
  return convertPower(btuh, 'Btu/h', 'kW');
}

/**
 * Format power with unit
 */
export function formatPower(value: number, unit: string = 'kW'): string {
  return `${value.toFixed(2)} ${unit}`;
}

/**
 * Format energy with unit (for accumulated values)
 */
export function formatEnergy(value: number, unit: string = 'kWh'): string {
  return `${value.toFixed(1)} ${unit}`;
}

// ============================================================
// Volume Conversions
// ============================================================

/**
 * Convert volume between units
 */
export function convertVolume(
  value: number,
  fromUnit: string,
  toUnit: string
): number {
  const num = HNum.make(value, fromUnit);
  const targetUnit = getVolumeUnit(toUnit);
  const converted = num.convertTo(targetUnit);
  return converted.value;
}

/**
 * Format volume with unit
 */
export function formatVolume(value: number, unit: string = 'L'): string {
  return `${value.toFixed(1)} ${unit}`;
}

// ============================================================
// Unit Helpers
// ============================================================

function getTemperatureUnit(unit: string) {
  switch (unit) {
    case '°C':
    case 'C':
      return celsius;
    case '°F':
    case 'F':
      return fahrenheit;
    case 'K':
      return kelvin;
    default:
      throw new Error(`Unknown temperature unit: ${unit}`);
  }
}

function getPressureUnit(unit: string) {
  switch (unit) {
    case 'Pa':
      return pascal;
    case 'kPa':
      return kilopascal;
    case 'bar':
      return bar;
    case 'psi':
      return poundsPerSquareInch;
    default:
      throw new Error(`Unknown pressure unit: ${unit}`);
  }
}

function getFlowUnit(unit: string) {
  switch (unit) {
    case 'm³/s':
    case 'm³/s':
      return cubicMetersPerSecond;
    case 'CFM':
    case 'cfm':
      return cubicFeetPerMinute;
    case 'L/s':
      return litersPerSecond;
    default:
      throw new Error(`Unknown flow unit: ${unit}`);
  }
}

function getPowerUnit(unit: string) {
  switch (unit) {
    case 'kW':
      return kilowatt;
    case 'W':
      return watt;
    default:
      throw new Error(`Unknown power unit: ${unit}`);
  }
}

function getVolumeUnit(unit: string) {
  switch (unit) {
    case 'm³':
      return cubicMeter;
    case 'L':
      return liter;
    case 'gal':
    case 'gpm':
      return gallon;
    default:
      throw new Error(`Unknown volume unit: ${unit}`);
  }
}

// ============================================================
// Display Formatting
// ============================================================

/**
 * Auto-format a numeric value with its unit
 * Detects common unit types and formats appropriately
 */
export function formatValue(value: number, unit: string): string {
  const lowerUnit = unit.toLowerCase();

  // Temperature
  if (lowerUnit.includes('c') || lowerUnit.includes('f') || lowerUnit.includes('k')) {
    return formatTemperature(value, unit);
  }

  // Pressure
  if (lowerUnit.includes('pa') || lowerUnit.includes('bar') || lowerUnit.includes('psi')) {
    return formatPressure(value, unit);
  }

  // Flow
  if (lowerUnit.includes('m³') || lowerUnit.includes('cfm') || lowerUnit.includes('l/s')) {
    return formatFlow(value, unit);
  }

  // Power
  if (lowerUnit.includes('kw') || lowerUnit.includes('btu') || lowerUnit.includes('ton')) {
    return formatPower(value, unit);
  }

  // Energy
  if (lowerUnit.includes('kwh') || lowerUnit.includes('j')) {
    return formatEnergy(value, unit);
  }

  // Default
  return `${value.toFixed(2)} ${unit}`;
}

/**
 * Get a display-safe unit symbol
 */
export function normalizeUnit(unit: string): string {
  const normalized = unit.trim();

  // Temperature
  if (normalized === 'C') return '°C';
  if (normalized === 'F') return '°F';

  // Power
  if (normalized.toLowerCase() === 'btu/h') return 'BTU/h';

  return normalized;
}
