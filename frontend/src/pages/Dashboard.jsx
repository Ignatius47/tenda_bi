import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useStore } from '../hooks/useStore'
import { useTheme } from '../hooks/useTheme'
import { dashApi, alertsApi } from '../api/client'
import { Loading, EmptyState, TrendBadge, DayPicker, InsightCard } from '../components/UI'

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = n => {
  n = Number(n || 0)
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}k`
  return `$${n.toFixed(0)}`
}

const normalizeHeader = value => String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '')
const toNumber = value => {
  if (value === null || value === undefined || value === '') return 0
  const cleaned = String(value).replace(/[$,\s]/g, '')
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : 0
}

function parseCsv(text) {
  const rows = []
  let row = []
  let cell = ''
  let inQuotes = false
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    const next = text[i + 1]
    if (char === '"') {
      if (inQuotes && next === '"') {
        cell += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }
    if (char === ',' && !inQuotes) {
      row.push(cell)
      cell = ''
      continue
    }
    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i += 1
      row.push(cell)
      if (row.some(col => String(col).trim() !== '')) rows.push(row)
      row = []
      cell = ''
      continue
    }
    cell += char
  }
  row.push(cell)
  if (row.some(col => String(col).trim() !== '')) rows.push(row)
  return rows
}

function mapUploadRows(rows) {
  if (!rows || rows.length < 2) return null
  const headers = rows[0].map(normalizeHeader)
  const fieldIndex = aliases => {
    for (const alias of aliases) {
      const idx = headers.indexOf(alias)
      if (idx >= 0) return idx
    }
    return -1
  }

  const idxDate = fieldIndex(['date', 'day', 'orderdate', 'createdat'])
  const idxRevenue = fieldIndex(['revenue', 'totalrevenue', 'sales', 'totalsales', 'amount'])
  const idxProfit = fieldIndex(['profit', 'totalprofit', 'grossprofit'])
  const idxOrders = fieldIndex(['orders', 'totalorders', 'ordercount'])

  if (idxDate < 0 || idxRevenue < 0) {
    throw new Error('Upload needs at least Date and Revenue columns.')
  }

  const trend = rows.slice(1).map((row, i) => {
    const rawDate = row[idxDate] || ''
    const dt = new Date(rawDate)
    const fallback = new Date(Date.now() - (rows.length - i) * 86400000)
    return {
      date: Number.isNaN(dt.getTime()) ? fallback.toISOString().slice(0, 10) : dt.toISOString().slice(0, 10),
      total_revenue: toNumber(row[idxRevenue]),
      total_profit: idxProfit >= 0 ? toNumber(row[idxProfit]) : 0,
      total_orders: idxOrders >= 0 ? toNumber(row[idxOrders]) : 0,
    }
  }).filter(r => r.total_revenue > 0 || r.total_profit > 0 || r.total_orders > 0)

  if (!trend.length) {
    throw new Error('No usable rows found in file.')
  }

  const nowTotal = trend.reduce((sum, item) => sum + item.total_revenue, 0)
  const nowProfit = trend.reduce((sum, item) => sum + item.total_profit, 0)
  const nowOrders = trend.reduce((sum, item) => sum + item.total_orders, 0)
  const split = Math.max(1, Math.floor(trend.length / 2))
  const prev = trend.slice(0, split)
  const curr = trend.slice(split)

  const pctChange = (current, previous) => {
    if (!previous) return current > 0 ? 100 : 0
    return ((current - previous) / previous) * 100
  }

  const prevRevenue = prev.reduce((sum, item) => sum + item.total_revenue, 0)
  const currRevenue = curr.reduce((sum, item) => sum + item.total_revenue, 0)
  const prevProfit = prev.reduce((sum, item) => sum + item.total_profit, 0)
  const currProfit = curr.reduce((sum, item) => sum + item.total_profit, 0)
  const prevOrders = prev.reduce((sum, item) => sum + item.total_orders, 0)
  const currOrders = curr.reduce((sum, item) => sum + item.total_orders, 0)
  const currentAov = nowOrders > 0 ? nowTotal / nowOrders : 0
  const previousAov = prevOrders > 0 ? prevRevenue / prevOrders : 0

  return {
    kpis: {
      revenue_30d: nowTotal,
      profit_30d: nowProfit,
      orders_30d: nowOrders,
      aov_30d: currentAov,
      revenue_change_pct: pctChange(currRevenue, prevRevenue),
      profit_change_pct: pctChange(currProfit, prevProfit),
      orders_change_pct: pctChange(currOrders, prevOrders),
      aov_change_pct: pctChange(currentAov, previousAov),
      repeat_purchase_rate: 0,
    },
    trend: trend.sort((a, b) => a.date.localeCompare(b.date)),
    products: [],
    insights: [{
      severity: 'info',
      insight_type: 'revenue',
      title: 'Custom file loaded',
      description: 'Dashboard is now showing metrics from your uploaded file.',
      action: 'Upload a new file anytime to refresh this view.',
    }],
    alerts: [],
  }
}

// ── Health score ──────────────────────────────────────────────────────────────
function calcHealth(kpis, alerts) {
  let score = 100
  const rev = Number(kpis?.revenue_change_pct || 0)
  const ord = Number(kpis?.orders_change_pct  || 0)
  if (rev < -20) score -= 25
  else if (rev < -10) score -= 15
  else if (rev < 0)   score -= 8
  else if (rev > 15)  score += 5
  if (ord < -20) score -= 15
  else if (ord < 0)   score -= 8
  const crits = (alerts || []).filter(a => a.severity === 'critical').length
  score -= crits * 10
  const repeat = Number(kpis?.repeat_purchase_rate || 0)
  if (repeat < 10) score -= 8
  else if (repeat > 30) score += 5
  return Math.max(0, Math.min(100, Math.round(score)))
}

function healthLabel(s) {
  if (s >= 80) return { label: 'Healthy',  color: '#10B981' }
  if (s >= 60) return { label: 'Moderate', color: '#F59E0B' }
  if (s >= 40) return { label: 'At Risk',  color: '#EF4444' }
  return             { label: 'Critical',  color: '#EF4444' }
}

// ── Cause detection ───────────────────────────────────────────────────────────
function detectCause(label, change, kpis) {
  const ord = Number(kpis?.orders_change_pct || 0)
  const aov = Number(kpis?.aov_change_pct    || 0)
  const rev = Number(kpis?.revenue_change_pct || 0)
  if (label === 'Total Revenue') {
    if (change < -10 && ord < -10) return 'Fewer orders this period'
    if (change < -10 && aov < -10) return 'Customers buying cheaper items'
    if (change > 15)  return '🚀 Strong momentum'
    if (change < -5)  return 'Check traffic or pricing'
  }
  if (label === 'Total Orders') {
    if (change > 20)  return '🚀 Demand accelerating'
    if (change < -20) return 'Traffic or conversion issue'
  }
  if (label === 'Avg Order Value') {
    if (change < -15 && ord > 10) return 'Customers buying smaller items'
    if (change > 10)  return '✅ Upsells working'
  }
  if (label === 'Gross Profit') {
    if (change < rev - 10) return 'Margins being squeezed'
    if (change > 10)  return '✅ Cost efficiency up'
  }
  return null
}

// ── Decision builder ──────────────────────────────────────────────────────────
function buildDecisions(kpis, alerts, products) {
  const decisions = []
  const rev = Number(kpis?.revenue_change_pct || 0)
  const ord = Number(kpis?.orders_change_pct  || 0)
  const aov = Number(kpis?.aov_change_pct     || 0)

  if (rev < -15) decisions.push({
    id: 'rev-drop', sev: 'critical', icon: '📉',
    title: `Revenue dropped ${Math.abs(rev).toFixed(0)}% vs last period`,
    reason: 'This is your most urgent issue. Something changed — check traffic sources, ad spend, and pricing.',
    action: 'View revenue trend', link: null,
  })

  if (ord > 10 && aov < -10) decisions.push({
    id: 'cheap', sev: 'warning', icon: '💸',
    title: 'Orders up but revenue is flat',
    reason: `Orders up ${ord.toFixed(0)}% but avg order down ${Math.abs(aov).toFixed(0)}% — customers are buying cheaper items.`,
    action: 'Bundle products or set a minimum order discount', link: '/products',
  })

  const critStock = (alerts || []).filter(a => a.category === 'stockout' && a.severity === 'critical')
  if (critStock.length > 0) decisions.push({
    id: 'stockout', sev: 'critical', icon: '🛑',
    title: `${critStock.length} product${critStock.length > 1 ? 's' : ''} at stockout risk`,
    reason: critStock[0]?.description || 'Stock runs out within 7 days. Every day you wait = lost sales.',
    action: 'Restock immediately', link: '/inventory',
  })

  const dead = (alerts || []).filter(a => a.category === 'inventory' && a.severity === 'warning')
  if (dead.length > 0) decisions.push({
    id: 'dead', sev: 'warning', icon: '📦',
    title: dead[0]?.title || 'Products tying up capital with no sales',
    reason: 'Dead stock blocks cash flow. Discounting often recovers more than sitting on it.',
    action: 'Discount, bundle, or remove', link: '/inventory?status=dead_stock',
  })

  const atRisk = (alerts || []).filter(a => a.category === 'customer')
  if (atRisk.length > 0) decisions.push({
    id: 'churn', sev: 'warning', icon: '👥',
    title: atRisk[0]?.title || 'Customers haven\'t returned in 45+ days',
    reason: atRisk[0]?.description || 'These customers are slipping away. A single win-back email can recover 10–20%.',
    action: 'Run a win-back campaign', link: '/customers?segment=At+Risk',
  })

  const opps = (alerts || []).filter(a => a.severity === 'success')
  if (opps.length > 0) decisions.push({
    id: 'opp', sev: 'success', icon: '🚀',
    title: opps[0]?.title || 'Trending product — act now',
    reason: opps[0]?.description || 'Demand is rising. Make sure stock can support this.',
    action: 'Increase stock and promote', link: '/products',
  })

  if (rev >= -5 && rev <= 5 && Number(kpis?.revenue_30d || 0) > 0) decisions.push({
    id: 'flat', sev: 'warning', icon: '📊',
    title: 'Revenue is flat — no growth this period',
    reason: 'Flat revenue usually means new customer acquisition has stalled or existing customers stopped returning.',
    action: 'Run a promotion or increase marketing', link: '/customers',
  })

  if (decisions.length === 0) decisions.push({
    id: 'sync', sev: 'info', icon: '🔄',
    title: 'Sync your store to unlock decisions',
    reason: 'No sales data found. Once synced, we\'ll tell you exactly what to do.',
    action: 'Click Sync Now', link: null,
  })

  return decisions.slice(0, 5)
}

// ── Sub-components ────────────────────────────────────────────────────────────
function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px', fontSize: 12, boxShadow: 'var(--shadow-lg)' }}>
      <div style={{ fontWeight: 600, color: 'var(--text-1)', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-2)', marginTop: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          {p.name}: <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>{p.name === 'orders' ? p.value : fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

function DecisionCard({ d, onSync, navigate }) {
  const C = {
    critical: { bg: 'rgba(239,68,68,.08)',  border: 'rgba(239,68,68,.28)',  btn: '#EF4444' },
    warning:  { bg: 'rgba(245,158,11,.08)', border: 'rgba(245,158,11,.28)', btn: '#F59E0B' },
    success:  { bg: 'rgba(16,185,129,.08)', border: 'rgba(16,185,129,.28)', btn: '#10B981' },
    info:     { bg: 'rgba(30,111,217,.08)', border: 'rgba(30,111,217,.28)', btn: '#1E6FD9' },
  }
  const c = C[d.sev] || C.info
  return (
    <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 12, padding: '14px 16px' }}>
      <div style={{ display: 'flex', gap: 12 }}>
        <span style={{ fontSize: 22, flexShrink: 0, lineHeight: 1.2 }}>{d.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>{d.title}</div>
          <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.55, marginBottom: 10 }}>{d.reason}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 11, color: 'var(--text-3)', fontStyle: 'italic' }}>→ {d.action}</div>
            {d.link ? (
              <button onClick={() => navigate(d.link)} style={{ marginLeft: 'auto', background: c.btn, color: '#fff', border: 'none', borderRadius: 7, fontSize: 11, fontWeight: 700, padding: '5px 12px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                Take action
              </button>
            ) : (
              <button onClick={onSync} style={{ marginLeft: 'auto', background: c.btn, color: '#fff', border: 'none', borderRadius: 7, fontSize: 11, fontWeight: 700, padding: '5px 12px', cursor: 'pointer' }}>
                Sync Now
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, change, accent, kpis }) {
  const up    = Number(change || 0) >= 0
  const cause = detectCause(label, Number(change || 0), kpis)
  return (
    <div className="card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: accent, borderRadius: '12px 12px 0 0' }} />
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.8px', color: 'var(--text-3)', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)', lineHeight: 1, marginBottom: 6, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: cause ? 5 : 0 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: up ? 'var(--green)' : 'var(--red)' }}>
          {up ? '▲' : '▼'} {Math.abs(Number(change || 0)).toFixed(1)}%
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>vs last period</span>
      </div>
      {cause && <div style={{ fontSize: 11, color: up ? '#059669' : 'var(--amber)', fontStyle: 'italic', lineHeight: 1.4 }}>{cause}</div>}
    </div>
  )
}

function PageHeader({ title, subtitle, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 24px', minHeight: 60, borderBottom: '1px solid var(--border)', background: 'var(--bg-card)', flexShrink: 0, flexWrap: 'wrap' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
        {subtitle && <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>{children}</div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { activeStore, triggerSync } = useStore()
  const { theme }                    = useTheme()
  const navigate                     = useNavigate()
  const ctx                          = useOutletContext() || {}
  const isMobile                     = ctx.isMobile
  const [days, setDays]              = useState(30)
  const [loading, setLoading]        = useState(true)
  const [syncing, setSyncing]        = useState(false)
  const [uploading, setUploading]    = useState(false)
  const [uploadError, setUploadError]= useState('')
  const [usingUpload, setUsingUpload]= useState(false)
  const [d, setD] = useState({ kpis: null, trend: [], products: [], insights: [], alerts: [] })
  const fileInputRef = useRef(null)
  const trendRef = useRef(null)

  const axisColor = theme === 'dark' ? '#4A5578' : '#8B9CC8'
  const gridColor = theme === 'dark' ? 'rgba(255,255,255,.04)' : 'rgba(0,0,0,.05)'

  const load = useCallback(async () => {
    if (!activeStore) { setLoading(false); return }
    setLoading(true)
    try {
      const [kpis, trend, products, insights, alertsData] = await Promise.all([
        dashApi.kpis(activeStore.id, days),
        dashApi.trend(activeStore.id, days),
        dashApi.products(activeStore.id, days, 8),
        dashApi.insights(activeStore.id),
        alertsApi.list(activeStore.id),
      ])
      setD({ kpis, trend, products, insights, alerts: alertsData.alerts || [] })
      setUsingUpload(false)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [activeStore, days])

  useEffect(() => { load() }, [load])

  const handleSync = async () => {
    setSyncing(true)
    try { await triggerSync(); await load() } finally { setSyncing(false) }
  }

  const handleUploadClick = () => fileInputRef.current?.click()

  const handleUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setUploadError('')
    setUploading(true)
    try {
      let rows = []
      if (file.name.toLowerCase().endsWith('.csv')) {
        const text = await file.text()
        rows = parseCsv(text)
      } else {
        const buffer = await file.arrayBuffer()
        const xlsx = await import('xlsx')
        const workbook = xlsx.read(buffer, { type: 'array' })
        const firstSheet = workbook.SheetNames[0]
        rows = xlsx.utils.sheet_to_json(workbook.Sheets[firstSheet], { header: 1, defval: '' })
      }
      const mapped = mapUploadRows(rows)
      if (!mapped) throw new Error('File is empty or unsupported.')
      setD(mapped)
      setUsingUpload(true)
    } catch (error) {
      setUploadError(error?.message || 'Could not process that file.')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const handleInsightAction = (insight) => {
    const actionText = String(insight?.action || '').toLowerCase()
    const type = String(insight?.insight_type || '').toLowerCase()

    if (actionText.includes('revenue') || type === 'revenue') {
      trendRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    if (actionText.includes('product') || type === 'product' || type === 'opportunity') {
      navigate('/products')
      return
    }
    if (actionText.includes('customer') || type === 'customer') {
      navigate('/customers')
      return
    }
    if (actionText.includes('inventory') || type === 'inventory') {
      navigate('/inventory')
      return
    }
    navigate('/alerts')
  }

  if (!activeStore) return (
    <div style={{ flex: 1 }}>
      {!isMobile && <PageHeader title="Dashboard" />}
      <div style={{ padding: 24 }}>
        <EmptyState icon="🛍️" title="No store connected"
          subtitle="Connect your Shopify store to start making data-driven decisions."
          action="Connect store" onAction={() => navigate('/connect')} />
      </div>
    </div>
  )

  const kpis      = d.kpis || {}
  const health    = calcHealth(kpis, d.alerts)
  const healthCfg = healthLabel(health)
  const decisions = buildDecisions(kpis, d.alerts, d.products)
  const hasTrend  = d.trend.some(t => Number(t.total_revenue) > 0)
  const critical  = d.alerts.filter(a => a.severity === 'critical').length

  const METRICS = [
    { label: 'Total Revenue',   value: fmt(kpis.revenue_30d),  change: kpis.revenue_change_pct, accent: 'linear-gradient(90deg,#10B981,#0ABFBC)' },
    { label: 'Gross Profit',    value: fmt(kpis.profit_30d),   change: kpis.profit_change_pct,  accent: 'linear-gradient(90deg,#1E6FD9,#0ABFBC)' },
    { label: 'Total Orders',    value: (kpis.orders_30d || 0).toLocaleString(), change: kpis.orders_change_pct, accent: 'linear-gradient(90deg,#8B5CF6,#EC4899)' },
    { label: 'Avg Order Value', value: `$${Number(kpis.aov_30d || 0).toFixed(2)}`, change: kpis.aov_change_pct, accent: 'linear-gradient(90deg,#F59E0B,#EF4444)' },
  ]

  // ── Mobile ──────────────────────────────────────────────────────────────────
  if (isMobile) return (
    <div className="fade-in" style={{ flex: 1 }}>
      <div style={{ padding: '14px 16px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', background: 'var(--bg-card)' }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>{activeStore.shop_name || 'Dashboard'}</div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>{new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={handleUploadClick} disabled={uploading} style={{ padding: '6px 10px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: uploading ? 'not-allowed' : 'pointer', border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-2)', opacity: uploading ? .7 : 1 }}>
            {uploading ? 'Uploading...' : 'Upload CSV/Excel'}
          </button>
          <div style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20, background: `${healthCfg.color}22`, color: healthCfg.color }}>{health}/100</div>
          <DayPicker value={days} onChange={setDays} />
        </div>
      </div>
      <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleUpload} style={{ display: 'none' }} />
      {uploadError && <div style={{ margin: '10px 16px 0', fontSize: 12, color: 'var(--red)' }}>{uploadError}</div>}
      {usingUpload && !uploadError && <div style={{ margin: '10px 16px 0', fontSize: 12, color: 'var(--text-3)' }}>Showing uploaded file data.</div>}

      {loading ? <Loading msg="Analysing your store…" /> : (
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-3)', marginBottom: 10 }}>Priority Actions</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
            {decisions.slice(0, 3).map(dec => <DecisionCard key={dec.id} d={dec} onSync={handleSync} navigate={navigate} />)}
          </div>

          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-3)', marginBottom: 10 }}>Key Metrics</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
            {METRICS.map(m => <MetricCard key={m.label} {...m} kpis={kpis} />)}
          </div>

          {hasTrend ? (
            <div className="card" style={{ marginBottom: 18, padding: '14px 16px' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 12 }}>Revenue Trend</div>
              <ResponsiveContainer width="100%" height={100}>
                <AreaChart data={d.trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#10B981" stopOpacity=".2" /><stop offset="100%" stopColor="#10B981" stopOpacity="0" /></linearGradient></defs>
                  <XAxis dataKey="date" tickFormatter={v => { const dt = new Date(v); return `${dt.getMonth()+1}/${dt.getDate()}` }} tick={{ fontSize: 9, fill: axisColor }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <Tooltip content={<ChartTip />} />
                  <Area type="monotone" dataKey="total_revenue" name="revenue" stroke="#10B981" strokeWidth={2} fill="url(#mg)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="card" style={{ marginBottom: 18, textAlign: 'center', padding: '20px 16px' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>📈</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)', marginBottom: 4 }}>No revenue data yet</div>
              <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Once orders come in, we'll track trends here.</div>
            </div>
          )}

          {d.products.length > 0 && (
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-3)' }}>Top Products</div>
                <button onClick={() => navigate('/products')} style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>View all →</button>
              </div>
              <div className="card" style={{ padding: 0 }}>
                {d.products.slice(0, 4).map((p, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
                    <div style={{ flex: 1, minWidth: 0, fontSize: 13, fontWeight: 500, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.title}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text-1)', flexShrink: 0 }}>{fmt(p.total_revenue)}</div>
                    <TrendBadge value={p.trend_pct || 0} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {d.alerts.length > 0 && (
            <button onClick={() => navigate('/alerts')} style={{ width: '100%', padding: 14, borderRadius: 12, background: critical > 0 ? 'var(--red-bg)' : 'var(--amber-bg)', border: `1px solid ${critical > 0 ? 'rgba(239,68,68,.3)' : 'rgba(245,158,11,.3)'}`, cursor: 'pointer', textAlign: 'left', marginBottom: 14 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 3 }}>
                {critical > 0 ? `🚨 ${critical} critical alert${critical > 1 ? 's' : ''}` : `📊 ${d.alerts.length} active alerts`}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>Tap to review and resolve →</div>
            </button>
          )}
        </div>
      )}
    </div>
  )

  // ── Desktop ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ flex: 1 }}>
      <PageHeader
        title={activeStore.shop_name || 'Dashboard'}
        subtitle={new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}>
        {/* Quick actions */}
        <button onClick={handleSync} disabled={syncing} style={{ padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: syncing ? 'not-allowed' : 'pointer', border: 'none', background: 'var(--brand-grad)', color: '#fff', boxShadow: '0 2px 10px rgba(30,111,217,.25)', opacity: syncing ? .7 : 1 }}>
          {syncing ? 'Syncing…' : 'Sync Store'}
        </button>
        <button onClick={handleUploadClick} disabled={uploading} style={{ padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: uploading ? 'not-allowed' : 'pointer', border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-2)', opacity: uploading ? .7 : 1 }}>
          {uploading ? 'Uploading...' : 'Upload CSV/Excel'}
        </button>
        <button onClick={() => navigate('/inventory')} style={{ padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-2)' }}>Inventory</button>
        <button onClick={() => navigate('/alerts')} style={{ padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-2)' }}>Alerts {critical > 0 && <span style={{ marginLeft: 4, background: 'var(--red)', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10 }}>{critical}</span>}</button>
        <DayPicker value={days} onChange={setDays} />
      </PageHeader>
      <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleUpload} style={{ display: 'none' }} />
      {uploadError && <div style={{ padding: '10px 24px 0', fontSize: 12, color: 'var(--red)' }}>{uploadError}</div>}
      {usingUpload && !uploadError && <div style={{ padding: '10px 24px 0', fontSize: 12, color: 'var(--text-3)' }}>Showing uploaded file data.</div>}

      {loading ? <Loading msg="Analysing your store data…" /> : (
        <div style={{ padding: '20px 24px' }} className="fade-in content-wrap">

          {/* ── HEALTH + WHAT CHANGED ──────────────────────────────────────── */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 20, padding: '16px 20px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, flexWrap: 'wrap' }}>

            {/* Health score ring */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, paddingRight: 20, borderRight: '1px solid var(--border)', flexShrink: 0 }}>
              <div style={{ position: 'relative', width: 56, height: 56 }}>
                <svg viewBox="0 0 56 56" style={{ width: 56, height: 56, transform: 'rotate(-90deg)' }}>
                  <circle cx="28" cy="28" r="22" fill="none" stroke="var(--border)" strokeWidth="5" />
                  <circle cx="28" cy="28" r="22" fill="none" stroke={healthCfg.color} strokeWidth="5"
                    strokeDasharray={`${(health / 100) * 138} 138`} strokeLinecap="round" />
                </svg>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color: healthCfg.color }}>{health}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.8px' }}>Store Health</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: healthCfg.color, lineHeight: 1.2 }}>{healthCfg.label}</div>
                <div style={{ fontSize: 11, color: 'var(--text-3)' }}>Score: {health}/100</div>
              </div>
            </div>

            {/* What changed */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.8px', marginBottom: 10 }}>📊 What Changed This Period</div>
              <div style={{ display: 'flex', gap: 0, flexWrap: 'wrap' }}>
                {[
                  ['Orders',    kpis.orders_change_pct,  (kpis.orders_30d || 0).toLocaleString() + ' total'],
                  ['Revenue',   kpis.revenue_change_pct, fmt(kpis.revenue_30d) + ' total'],
                  ['Avg Order', kpis.aov_change_pct,     `$${Number(kpis.aov_30d || 0).toFixed(2)} avg`],
                  ['Profit',    kpis.profit_change_pct,  fmt(kpis.profit_30d) + ' total'],
                ].map(([label, change, sub]) => {
                  const up = Number(change || 0) >= 0
                  return (
                    <div key={label} style={{ flex: 1, minWidth: 90, padding: '0 14px', borderRight: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 3 }}>{label}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: up ? 'var(--green)' : 'var(--red)', lineHeight: 1 }}>
                        {up ? '+' : ''}{Number(change || 0).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 2 }}>{sub}</div>
                    </div>
                  )
                })}
              </div>

              {/* Narrative */}
              {(() => {
                const ord = Number(kpis.orders_change_pct || 0)
                const rev = Number(kpis.revenue_change_pct || 0)
                const aov = Number(kpis.aov_change_pct || 0)
                let n = null
                if (ord > 10 && aov < -10) n = { icon: '💸', text: 'Orders increased but average order value dropped — customers are buying cheaper items. Consider bundles or minimum order discounts.' }
                else if (rev < -15) n = { icon: '🚨', text: 'Revenue is falling significantly. Check traffic sources, ad spend, pricing, and whether key products are still in stock.' }
                else if (rev > 15 && ord > 10) n = { icon: '🚀', text: 'Strong growth across orders and revenue. Make sure stock levels can support this demand — check inventory now.' }
                else if (Math.abs(rev) < 3 && Number(kpis.revenue_30d || 0) > 0) n = { icon: '📊', text: 'Revenue is flat. You may have plateaued with your current audience. Consider a promotion or new marketing channel.' }
                if (!n) return null
                return (
                  <div style={{ marginTop: 10, padding: '8px 12px', background: 'var(--bg-surface)', borderRadius: 8, fontSize: 12, color: 'var(--text-2)', display: 'flex', gap: 8 }}>
                    <span style={{ flexShrink: 0 }}>{n.icon}</span> {n.text}
                  </div>
                )
              })()}
            </div>
          </div>

          {/* ── TODAY'S ACTIONS ─────────────────────────────────────────────── */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>Priority Actions</div>
              <div style={{ fontSize: 12, color: 'var(--text-3)' }}>What needs your attention right now</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
              {decisions.map(dec => <DecisionCard key={dec.id} d={dec} onSync={handleSync} navigate={navigate} />)}
            </div>
          </div>

          {/* ── KEY METRICS ─────────────────────────────────────────────────── */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-3)', marginBottom: 12 }}>Key Metrics - Last {days} days</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14 }}>
              {METRICS.map(m => <MetricCard key={m.label} {...m} kpis={kpis} />)}
            </div>
          </div>

          {/* ── CHART + INSIGHTS ────────────────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 290px', gap: 16, marginBottom: 20 }}>
            {hasTrend ? (
              <div className="card" ref={trendRef}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>Revenue & Profit Trend</div>
                    <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>Daily · Last {days} days</div>
                  </div>
                  <TrendBadge value={kpis.revenue_change_pct || 0} />
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={d.trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10B981" stopOpacity=".15" />
                        <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                    <XAxis dataKey="date" tickFormatter={v => { const dt = new Date(v); return `${dt.getMonth()+1}/${dt.getDate()}` }} tick={{ fontSize: 10, fill: axisColor }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                    <YAxis tickFormatter={v => `$${(v/1000).toFixed(0)}k`} tick={{ fontSize: 10, fill: axisColor }} axisLine={false} tickLine={false} width={44} />
                    <Tooltip content={<ChartTip />} />
                    <Area type="monotone" dataKey="total_revenue" name="revenue" stroke="#10B981" strokeWidth={2.5} fill="url(#rg)" dot={false} activeDot={{ r: 5, fill: '#10B981', strokeWidth: 0 }} />
                    <Area type="monotone" dataKey="total_profit"  name="profit"  stroke="#1E6FD9" strokeWidth={1.8} fill="none" strokeDasharray="5 3" dot={false} activeDot={{ r: 4 }} />
                  </AreaChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                  {[['#10B981', 'Revenue'], ['#1E6FD9', 'Profit']].map(([c, l]) => (
                    <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
                      <div style={{ width: 14, height: 2, background: c, borderRadius: 1 }} />{l}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 260 }} ref={trendRef}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>📈</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6 }}>No revenue data yet</div>
                <div style={{ fontSize: 13, color: 'var(--text-3)', textAlign: 'center', maxWidth: 260 }}>Once orders come in, we'll track your daily revenue and profit trend here.</div>
                <button onClick={handleSync} style={{ marginTop: 16, padding: '9px 20px', borderRadius: 9, background: 'var(--brand-grad)', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Sync store now</button>
              </div>
            )}

            {/* AI Insights */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>Insights</div>
                <div style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 20, background: 'rgba(16,185,129,.12)', color: 'var(--green)' }}>● LIVE</div>
              </div>
              {d.insights.length > 0
                ? d.insights.slice(0, 5).map((ins, i) => (
                    <InsightCard key={i} type={ins.severity}
                      icon={ins.insight_type === 'revenue' ? '📈' : ins.insight_type === 'product' ? '🏆' : ins.insight_type === 'customer' ? '👥' : '💡'}
                      title={ins.title} description={ins.description} action={ins.action}
                      onAction={() => handleInsightAction(ins)} />
                  ))
                : (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '20px 0' }}>
                    <div style={{ fontSize: 32, marginBottom: 10 }}>🤖</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6 }}>Insights generating…</div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Sync your store to unlock AI recommendations.</div>
                  </div>
                )}
            </div>
          </div>

          {/* ── PRODUCTS: Winners + Losers ───────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16, marginBottom: 20 }}>
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>🏆 Top Performers</div>
                <button onClick={() => navigate('/products')} style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>View all →</button>
              </div>
              {d.products.length === 0
                ? <div style={{ textAlign: 'center', padding: '24px 0' }}><div style={{ fontSize: 28, marginBottom: 8 }}>📦</div><div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)', marginBottom: 4 }}>No product data</div><div style={{ fontSize: 12, color: 'var(--text-3)' }}>Sync your store to see performance.</div></div>
                : d.products.filter(p => Number(p.trend_pct || 0) >= 0 || Number(p.total_revenue || 0) > 0).slice(0, 4).map((p, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
                      <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.title}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>{p.units_sold || 0} units · {fmt(p.total_revenue)}</div>
                      </div>
                      <TrendBadge value={p.trend_pct || 0} />
                      <button onClick={() => navigate('/products')} style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(16,185,129,.1)', color: 'var(--green)', border: 'none', fontSize: 10, fontWeight: 600, cursor: 'pointer', flexShrink: 0 }}>Promote</button>
                    </div>
                  ))
              }
            </div>

            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>📉 Needs Attention</div>
                <button onClick={() => navigate('/inventory')} style={{ background: 'none', border: 'none', color: 'var(--amber)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Review →</button>
              </div>
              {d.products.length === 0
                ? <div style={{ textAlign: 'center', padding: '24px 0' }}><div style={{ fontSize: 28, marginBottom: 8 }}>✅</div><div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)' }}>All products look healthy</div></div>
                : (() => {
                    const under = d.products.filter(p => Number(p.trend_pct || 0) < -10 || Number(p.total_revenue || 0) === 0).slice(0, 4)
                    if (under.length === 0) return <div style={{ textAlign: 'center', padding: '24px 0' }}><div style={{ fontSize: 28, marginBottom: 8 }}>✅</div><div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)' }}>All products performing well</div></div>
                    return under.map((p, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: i < under.length - 1 ? '1px solid var(--border)' : 'none' }}>
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--amber)', flexShrink: 0 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.title}</div>
                          <div style={{ fontSize: 10, color: 'var(--text-3)' }}>{Number(p.total_revenue || 0) === 0 ? 'No sales this period' : 'Sales declining'}</div>
                        </div>
                        <TrendBadge value={p.trend_pct || 0} />
                        <button style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(245,158,11,.1)', color: 'var(--amber)', border: 'none', fontSize: 10, fontWeight: 600, cursor: 'pointer', flexShrink: 0 }}>Discount</button>
                      </div>
                    ))
                  })()
              }
            </div>
          </div>

          {/* ── Daily orders bar ─────────────────────────────────────────────── */}
          {hasTrend && (
            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)', marginBottom: 14 }}>Daily Orders</div>
              <ResponsiveContainer width="100%" height={110}>
                <BarChart data={d.trend} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={v => { const dt = new Date(v); return `${dt.getMonth()+1}/${dt.getDate()}` }} tick={{ fontSize: 10, fill: axisColor }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: axisColor }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip content={<ChartTip />} />
                  <Bar dataKey="total_orders" name="orders" fill="#1E6FD9" radius={[3, 3, 0, 0]} opacity={0.85} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
