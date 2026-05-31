// Mirrors app/components/cards/kpi_card.py `_format_value` exactly.

export function formatValue(value, kind) {
  if (value === null || value === undefined) return '—';
  if (kind === 'money') {
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (kind === 'money_compact') {
    const sign = value > 0 ? '+' : '';
    return sign + '$' + Math.round(value).toLocaleString('en-US');
  }
  if (kind === 'percent') {
    const sign = value > 0 ? '+' : '';
    return sign + (value * 100).toFixed(2) + '%';
  }
  if (kind === 'ratio') {
    return value.toFixed(2);
  }
  return String(value);
}

// Sign class for money_compact / percent KPIs.
export function valueClass(value, kind) {
  if ((kind === 'money_compact' || kind === 'percent') && value !== null && value !== undefined) {
    return value >= 0 ? 'kpi-value-up' : 'kpi-value-down';
  }
  return '';
}

// Column formatters for the positions table (mirror investments.py specifiers).
export const fmt = {
  shares: (v) => v == null ? '' : v.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 }),
  money2: (v) => v == null ? '' : '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  signedMoney2: (v) => v == null ? '' : (v >= 0 ? '+' : '−') + '$' + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  signedPct2: (v) => v == null ? '' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2),
  pct1: (v) => v == null ? '' : v.toFixed(1)
};
