import React from 'react'

/* ── Icons (inline SVG — no dependency needed) ───────────────────────────── */
export const Icon = {
  dashboard:  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>,
  products:   <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>,
  inventory:  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3h18v18H3z" rx="2"/><path d="M3 9h18M9 21V9"/></svg>,
  customers:  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  alerts:     <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>,
  sun:        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  moon:       <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
  sync:       <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  add:        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  chevronL:   <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>,
  chevronR:   <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>,
  menu:       <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>,
  close:      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  logout:     <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  check:      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
  store:      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
  up:         <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="18 15 12 9 6 15"/></svg>,
  down:       <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="6 9 12 15 18 9"/></svg>,
}

/* ── Topbar ──────────────────────────────────────────────────────────────── */
export function Topbar({ title, subtitle, onMenuClick, children }) {
  return (
    <header style={{
      height: 'var(--topbar-h)',
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '0 24px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--bg-card)',
      position: 'sticky', top: 0, zIndex: 20,
      flexShrink: 0,
    }}>
      {/* Mobile menu button */}
      <button onClick={onMenuClick} style={{
        display: 'none', alignItems: 'center', justifyContent: 'center',
        width: 36, height: 36, borderRadius: 8,
        background: 'transparent', border: '1px solid var(--border)',
        color: 'var(--text-secondary)', flexShrink: 0,
        ['@media (max-width: 768px)']: { display: 'flex' },
      }} className="mobile-menu-btn">
        {Icon.menu}
      </button>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
        {subtitle && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        {children}
      </div>
    </header>
  )
}

/* ── Content wrapper ─────────────────────────────────────────────────────── */
export function Content({ children, style }) {
  return (
    <div className="fade-in content-wrap" style={{ padding: '20px 24px', flex: 1, ...style }}>
      {children}
    </div>
  )
}

/* ── Responsive grid ─────────────────────────────────────────────────────── */
export function Grid({ cols = 4, gap = 14, children, style, minW = 200 }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(auto-fit, minmax(${minW}px, 1fr))`,
      gap,
      ...style,
    }}>
      {children}
    </div>
  )
}

/* ── KPI Card ────────────────────────────────────────────────────────────── */
export function KPICard({ label, value, change, icon, barPct, barColor = 'var(--green)', accent }) {
  const up = change >= 0
  return (
    <div className="card" style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden' }}>
      {/* Subtle gradient accent top border */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: accent || 'var(--brand-grad)',
        borderRadius: '12px 12px 0 0',
      }} />

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--text-muted)' }}>
          {label}
        </div>
        {icon && (
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'rgba(30,111,217,0.10)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--brand-blue)',
          }}>{icon}</div>
        )}
      </div>

      <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1, marginBottom: 8, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>

      {change !== undefined && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}
          className={up ? 'trend-up' : 'trend-down'}>
          <span style={{ display: 'flex', alignItems: 'center' }}>{up ? Icon.up : Icon.down}</span>
          <span style={{ fontWeight: 600 }}>{Math.abs(change).toFixed(1)}%</span>
          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>vs last period</span>
        </div>
      )}

      {barPct !== undefined && (
        <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginTop: 12, overflow: 'hidden' }}>
          <div style={{
            width: `${Math.min(100, barPct)}%`, height: '100%',
            background: barColor, borderRadius: 2,
            transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
          }} />
        </div>
      )}
    </div>
  )
}

/* ── Insight card ────────────────────────────────────────────────────────── */
export function InsightCard({ type = 'info', icon, title, description, action, onAction }) {
  const C = {
    success: ['var(--green)',      'var(--green-bg)'],
    danger:  ['var(--red)',        'var(--red-bg)'],
    warning: ['var(--amber)',      'var(--amber-bg)'],
    info:    ['var(--brand-blue)', 'var(--blue-bg)'],
  }
  const [border, bg] = C[type] || C.info
  return (
    <div style={{
      display: 'flex', gap: 12, padding: '12px 14px',
      background: bg, borderRadius: 10,
      borderLeft: `3px solid ${border}`,
    }}>
      {icon && <div style={{ fontSize: 17, flexShrink: 0, marginTop: 1 }}>{icon}</div>}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>{title}</div>
        {description && <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{description}</div>}
        {action && (
          <button onClick={onAction} style={{
            background: 'none', border: 'none', color: border,
            fontSize: 11, fontWeight: 600, cursor: 'pointer', marginTop: 6, padding: 0,
            display: 'flex', alignItems: 'center', gap: 3,
          }}>
            {action} {Icon.chevronR}
          </button>
        )}
      </div>
    </div>
  )
}

/* ── Loading ─────────────────────────────────────────────────────────────── */
export function Loading({ msg = 'Loading…' }) {
  return (
    <div className="page-loading">
      <div className="spinner" />
      <span>{msg}</span>
    </div>
  )
}

/* ── Empty state ─────────────────────────────────────────────────────────── */
export function EmptyState({ icon = '📭', title, subtitle, action, onAction }) {
  return (
    <div style={{ textAlign: 'center', padding: '56px 24px', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: 40, marginBottom: 16, opacity: 0.7 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>{title}</div>
      {subtitle && <div style={{ fontSize: 13, marginBottom: 20, maxWidth: 320, margin: '0 auto 20px' }}>{subtitle}</div>}
      {action && (
        <button onClick={onAction} style={{
          padding: '10px 22px', borderRadius: 10,
          background: 'var(--brand-grad)', color: '#fff',
          border: 'none', fontSize: 13, fontWeight: 600,
          cursor: 'pointer', boxShadow: '0 4px 14px rgba(30,111,217,0.3)',
        }}>
          {action}
        </button>
      )}
    </div>
  )
}

/* ── Trend badge ─────────────────────────────────────────────────────────── */
export function TrendBadge({ value }) {
  const up = value >= 0
  return (
    <span className={`badge ${up ? 'badge-green' : 'badge-red'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
      {up ? Icon.up : Icon.down}
      {Math.abs(value).toFixed(1)}%
    </span>
  )
}

/* ── Status pill ─────────────────────────────────────────────────────────── */
export function StatusPill({ status }) {
  const M = {
    critical:   ['Critical',   'badge-red'],
    low:        ['Low',        'badge-amber'],
    ok:         ['Healthy',    'badge-green'],
    dead_stock: ['Dead Stock', 'badge-gray'],
  }
  const [label, cls] = M[status] || [status, 'badge-gray']
  return <span className={`badge ${cls}`}>{label}</span>
}

/* ── Day range picker ────────────────────────────────────────────────────── */
export function DayPicker({ value, onChange }) {
  return (
    <div className="day-picker" style={{
      display: 'flex', gap: 2,
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 10, padding: 3,
    }}>
      {[7, 14, 30, 90].map(d => (
        <button className="day-picker-btn" key={d} onClick={() => onChange(d)} style={{
          padding: '4px 12px', borderRadius: 7,
          fontSize: 12, fontWeight: 500, border: 'none',
          background: value === d ? 'var(--bg-card)' : 'transparent',
          color: value === d ? 'var(--text-primary)' : 'var(--text-muted)',
          boxShadow: value === d ? 'var(--shadow-sm)' : 'none',
          cursor: 'pointer', transition: 'all 0.15s',
        }}>
          {d}d
        </button>
      ))}
    </div>
  )
}

/* ── Theme toggle ────────────────────────────────────────────────────────── */
export function ThemeToggle({ theme, onToggle }) {
  return (
    <button onClick={onToggle} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} style={{
      width: 36, height: 36, borderRadius: 9,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      color: 'var(--text-secondary)',
      cursor: 'pointer', transition: 'all 0.15s', flexShrink: 0,
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-strong)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      {theme === 'dark' ? Icon.sun : Icon.moon}
    </button>
  )
}

/* ── Filter chip ─────────────────────────────────────────────────────────── */
export function FilterChip({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 12px', borderRadius: 8,
      fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
      background: active ? 'var(--bg-card)' : 'transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-muted)',
      boxShadow: active ? 'var(--shadow-sm)' : 'none',
      transition: 'all 0.12s',
    }}>
      {children}
    </button>
  )
}

/* ── Search input ────────────────────────────────────────────────────────── */
export function SearchInput({ value, onChange, placeholder = 'Search…' }) {
  return (
    <div className="search-wrap" style={{ position: 'relative', flex: 1, maxWidth: 280 }}>
      <svg style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}
        width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input
        value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: '100%', padding: '7px 12px 7px 32px',
          border: '1px solid var(--border)', borderRadius: 9,
          background: 'var(--bg-input)', color: 'var(--text-primary)',
          fontSize: 13, fontFamily: 'var(--font)', outline: 'none',
          transition: 'border-color 0.15s',
        }}
        onFocus={e => e.target.style.borderColor = 'var(--brand-blue)'}
        onBlur={e => e.target.style.borderColor = 'var(--border)'}
      />
    </div>
  )
}

/* ── Data table wrapper ──────────────────────────────────────────────────── */
export function DataTable({ headers, children, empty }) {
  return (
    <div className="card data-table-wrap" style={{ padding: 0, overflow: 'hidden' }}>
      <div className="data-table-scroll" style={{ overflowX: 'auto' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {headers.map((h, i) => (
                <th key={i} style={{
                  padding: '12px 16px', textAlign: 'left',
                  fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '0.8px', color: 'var(--text-muted)',
                  whiteSpace: 'nowrap', background: 'var(--bg-card)',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
        {empty}
      </div>
    </div>
  )
}

/* ── Table row ───────────────────────────────────────────────────────────── */
export function TR({ children, onClick }) {
  return (
    <tr
      className="data-row"
      onClick={onClick}
      style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.1s', cursor: onClick ? 'pointer' : 'default' }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      {children}
    </tr>
  )
}

/* ── Table cell ──────────────────────────────────────────────────────────── */
export function TD({ children, mono, muted, fw, align = 'left' }) {
  return (
    <td className="data-cell" style={{
      padding: '11px 16px',
      fontSize: 13,
      color: muted ? 'var(--text-muted)' : 'var(--text-primary)',
      fontFamily: mono ? 'var(--mono)' : 'var(--font)',
      fontWeight: fw || (mono ? 500 : 400),
      textAlign: align,
      whiteSpace: 'nowrap',
    }}>
      {children}
    </td>
  )
}

/* ── Alert card ──────────────────────────────────────────────────────────── */
export function AlertCard({ alert, onResolve }) {
  const SEV = {
    critical: { color: 'var(--red)',         bg: 'var(--red-bg)',   icon: '🚨', label: 'Critical' },
    warning:  { color: 'var(--amber)',        bg: 'var(--amber-bg)', icon: '⚠️', label: 'Warning' },
    info:     { color: 'var(--brand-blue)',   bg: 'var(--blue-bg)',  icon: '💡', label: 'Info' },
    success:  { color: 'var(--green)',        bg: 'var(--green-bg)', icon: '✅', label: 'Opportunity' },
  }
  const cfg = SEV[alert.severity] || SEV.info
  return (
    <div style={{
      display: 'flex', gap: 14, padding: '16px 18px',
      background: cfg.bg, borderRadius: 12,
      border: `1px solid ${cfg.color}33`,
      marginBottom: 10,
    }}>
      <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>{cfg.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{alert.title}</div>
          <span className="badge" style={{ background: `${cfg.color}22`, color: cfg.color, fontSize: 10 }}>{cfg.label.toUpperCase()}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{alert.description}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
          {alert.action_label && (
            <button style={{
              background: cfg.color, color: '#fff',
              border: 'none', borderRadius: 7,
              fontSize: 12, fontWeight: 600, padding: '5px 14px', cursor: 'pointer',
            }}>
              {alert.action_label}
            </button>
          )}
          {onResolve && (
            <button onClick={() => onResolve(alert.id)} style={{
              background: 'transparent', border: '1px solid var(--border)',
              borderRadius: 7, color: 'var(--text-muted)',
              fontSize: 12, padding: '5px 12px', cursor: 'pointer',
            }}>
              Resolve
            </button>
          )}
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>
            {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  )
}
