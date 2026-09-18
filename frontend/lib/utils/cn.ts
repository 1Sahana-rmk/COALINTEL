import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMetricNumber(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === '') return 'N/A';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return 'N/A';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(num);
}

export function formatStandardValue(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === '') return '0.00';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return String(val);
  if (num === 0) return '0.00';
  const absNum = Math.abs(num);
  if (absNum >= 1) {
    return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (absNum >= 0.01) {
    return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  }
  // For small fractional numbers (e.g. 7.99 Tonnes -> 0.000008 MT), format with up to 6 decimals without trailing zeroes
  const formatted = num.toFixed(6).replace(/\.?0+$/, '');
  return formatted || num.toString();
}
