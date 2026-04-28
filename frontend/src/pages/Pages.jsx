import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { useStore } from '../hooks/useStore'
import { useTheme } from '../hooks/useTheme'
import { dashApi, inventoryApi, customerApi, alertsApi } from '../api/client'
import {
  Content, Grid, KPICard, InsightCard, Loading, EmptyState,
  TrendBadge, StatusPill, DayPicker, SearchInput,
  DataTable, TR, TD, AlertCard, Icon,
} from '../components/UI'

/* ─── Page header (shared) ──────────────────────────────────────────────── */
function PageHeader({ title, subtitle, children }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 24px', minHeight: 'var(--topbar-h)',
      borderBottom: '1px solid var(--border)',
      background: 'var(--bg-card)', flexShrink: 0, flexWrap: 'wrap',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
        {subtitle && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>{children}</div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════
   PRODUCTS
═══════════════════════════════════════════════════════════════════════ */
export function Products() {
  const { activeStore } = useStore()
  const ctx = useOutletContext() || {}
  const isMobile = !!ctx.isMobile
  const [days, setDays]       = useState(30)
  const [loading, setLoading] = useState(true)
  const [products, setProducts] = useState([])
  const [search, setSearch]   = useState('')
  const [sort, setSort]       = useState('total_revenue')

  const load = useCallback(async () => {
    if (!activeStore) { setLoading(false); return }
    setLoading(true)
    try { setProducts(await dashApi.products(activeStore.id, days, 50)) }
    catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [activeStore, days])

  useEffect(() => { load() }, [load])
  const SORTS = [
    ['total_revenue', 'Revenue'],
    ['units_sold', 'Units'],
    ['margin_pct', 'Margin'],
    ['trend_pct', 'Trend'],
  ]

  const filtered = products
    .filter(p => !search || p.title?.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => (Number(b[sort]) || 0) - (Number(a[sort]) || 0))

  return (
    <div style={{ flex: 1 }}>
      <PageHeader title="Products" subtitle="Revenue - Profit - Trend Analysis">
        <DayPicker value={days} onChange={setDays} />
      </PageHeader>

      {loading ? <Loading /> : (
        <Content>
          {/* Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
            <SearchInput value={search} onChange={setSearch} placeholder="Search products..." />
            <div style={{ display: 'flex', gap: 4, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 3, width: isMobile ? '100%' : 'auto', overflowX: 'auto' }}>
              {SORTS.map(([k, l]) => (
                <button key={k} onClick={() => setSort(k)} style={{
                  padding: '4px 11px', borderRadius: 7, fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
                  background: sort === k ? 'var(--bg-card)' : 'transparent',
                  color: sort === k ? 'var(--text-primary)' : 'var(--text-muted)',
                  boxShadow: sort === k ? 'var(--shadow-sm)' : 'none',
                  transition: 'all 0.12s',
                }}>{l}</button>
              ))}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {filtered.length} products
            </div>
          </div>

          {filtered.length === 0
            ? <EmptyState icon="📦" title="No products found" subtitle="Try adjusting filters or connect your Shopify store." />
            : (
              <DataTable headers={['#', 'Product', 'Category', 'Revenue', 'Units', 'Margin', 'Trend']}>
                {filtered.map((p, i) => (
                  <TR key={p.product_id || i}>
                    <TD mono muted>{i + 1}</TD>
                    <TD>
                      <div style={{ fontWeight: 500 }}>{p.title}</div>
                    </TD>
                    <TD><span className="badge badge-brand">{p.category || 'Uncategorized'}</span></TD>
                    <TD mono fw={700}>${Number(p.total_revenue || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</TD>
                    <TD mono>{(p.units_sold || 0).toLocaleString()}</TD>
                    <TD>
                      <span className={`badge ${Number(p.margin_pct) >= 40 ? 'badge-green' : Number(p.margin_pct) >= 20 ? 'badge-blue' : 'badge-amber'}`}>
                        {Number(p.margin_pct || 0).toFixed(1)}%
                      </span>
                    </TD>
                    <TD><TrendBadge value={p.trend_pct || 0} /></TD>
                  </TR>
                ))}
              </DataTable>
            )}
        </Content>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════
   INVENTORY
═══════════════════════════════════════════════════════════════════════ */
export function Inventory() {
  const { activeStore } = useStore()
  const ctx = useOutletContext() || {}
  const isMobile = !!ctx.isMobile
  const [loading, setLoading] = useState(true)
  const [inv, setInv]         = useState(null)
  const [filter, setFilter]   = useState('all')

  const FILTERS = [
    ['all', 'All'],
    ['critical', '⚠ Critical'],
    ['low', 'Low Stock'],
    ['dead_stock', 'Dead Stock'],
    ['ok', 'Healthy'],
  ]

  const load = useCallback(async () => {
    if (!activeStore) { setLoading(false); return }
    setLoading(true)
    try { setInv(await inventoryApi.overview(activeStore.id)) }
    catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [activeStore])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!activeStore) return undefined
    const timer = setInterval(() => { load() }, 15000)
    return () => clearInterval(timer)
  }, [activeStore, load])

  const items = (inv?.items || []).filter(i => filter === 'all' || i.status === filter)

  return (
    <div style={{ flex: 1 }}>
      <PageHeader title="Inventory Health" subtitle="Stock Cover - Dead Stock - Restock Alerts">
        <div style={{ display: 'flex', gap: 3, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 3, flexWrap: 'wrap', width: isMobile ? '100%' : 'auto' }}>
          {FILTERS.map(([k, l]) => (
            <button key={k} onClick={() => setFilter(k)} style={{
              padding: '4px 11px', borderRadius: 7, fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
              background: filter === k ? 'var(--bg-card)' : 'transparent',
              color: filter === k ? 'var(--text-primary)' : 'var(--text-muted)',
              boxShadow: filter === k ? 'var(--shadow-sm)' : 'none',
              transition: 'all 0.12s', whiteSpace: 'nowrap',
            }}>{l}</button>
          ))}
        </div>
      </PageHeader>

      {loading ? <Loading /> : (
        <Content>
          <div className="section-title">Overview</div>
          <Grid cols={4} gap={12} minW={isMobile ? 140 : 160} style={{ marginBottom: 20 }}>
            <KPICard label="Avg Stock Cover"  value={`${inv?.summary?.avg_days_cover ?? 0}d`}    accent="var(--brand-grad)" />
            <KPICard label="Stockout Risk"    value={String(inv?.summary?.critical_count ?? 0)}  barPct={inv?.summary?.critical_count > 0 ? 100 : 0} barColor="var(--red)"   accent="linear-gradient(90deg,#EF4444,#F59E0B)" />
            <KPICard label="Dead Stock SKUs"  value={String(inv?.summary?.dead_stock_count ?? 0)} barPct={40} barColor="var(--amber)" accent="linear-gradient(90deg,#F59E0B,#F97316)" />
            <KPICard label="Total SKUs"       value={String(inv?.summary?.total_skus ?? 0)}       accent="linear-gradient(90deg,#8B5CF6,#1E6FD9)" />
          </Grid>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
            Live products in store: <strong style={{ color: 'var(--text-primary)' }}>{inv?.summary?.total_products_live ?? 0}</strong>
            {' '}({inv?.summary?.total_variants_live ?? 0} variants)
          </div>

          {items.length === 0
            ? <EmptyState icon="📦" title="No inventory data" subtitle="Connect and sync your Shopify store to see stock health." />
            : (
              <DataTable headers={['Product', 'SKU', 'Stock', 'Daily Sales', 'Days Cover', 'Status', 'Action']}>
                {items.map(item => (
                  <TR key={item.variant_id}>
                    <TD>
                      <div style={{ fontWeight: 500 }}>{item.product_title}</div>
                      {item.variant_title && item.variant_title !== 'Default Title' && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.variant_title}</div>
                      )}
                    </TD>
                    <TD mono muted>{item.sku || '—'}</TD>
                    <TD mono fw={700}>{item.stock_quantity}</TD>
                    <TD mono muted>{Number(item.avg_daily_sales || 0).toFixed(1)}/day</TD>
                    <TD>
                      <span style={{
                        fontSize: 13, fontFamily: 'var(--mono)', fontWeight: 700,
                        color: item.days_cover <= 7 ? 'var(--red)' : item.days_cover <= 14 ? 'var(--amber)' : 'var(--green)',
                      }}>
                        {item.days_cover >= 999 ? '∞' : `${Math.round(item.days_cover)}d`}
                      </span>
                    </TD>
                    <TD><StatusPill status={item.status} /></TD>
                    <TD>
                      {item.status !== 'ok' ? (
                        <button style={{
                          background: 'var(--brand-grad)', color: '#fff',
                          border: 'none', borderRadius: 7, fontSize: 11, fontWeight: 600,
                          padding: '4px 12px', cursor: 'pointer',
                        }}>
                          {item.status === 'dead_stock' ? 'Review' : 'Restock'}
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>
                      )}
                    </TD>
                  </TR>
                ))}
              </DataTable>
            )}
        </Content>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════
   CUSTOMERS
═══════════════════════════════════════════════════════════════════════ */
const SEG_ICONS  = { VIP: '👑', Loyal: '🌟', New: '🌱', 'At Risk': '⚠️', Lost: '💤' }
const SEG_COLORS = { VIP: '#10B981', Loyal: '#1E6FD9', New: '#8B5CF6', 'At Risk': '#F59E0B', Lost: '#EF4444' }

export function Customers() {
  const { activeStore } = useStore()
  const ctx             = useOutletContext() || {}
  const isMobile        = !!ctx.isMobile
  const navigate        = useNavigate()
  const [loading, setLoading]   = useState(true)
  const [analytics, setAnalytics] = useState(null)
  const [customers, setCustomers] = useState([])
  const [activeSeg, setActiveSeg] = useState(null)
  const [search, setSearch]       = useState('')

  const load = useCallback(async () => {
    if (!activeStore) { setLoading(false); return }
    setLoading(true)
    try {
      const [ana, custs] = await Promise.all([
        customerApi.analytics(activeStore.id),
        customerApi.list(activeStore.id, { page: 1, page_size: 50 }),
      ])
      setAnalytics(ana)
      setCustomers(custs.results || [])
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [activeStore])

  useEffect(() => { load() }, [load])

  const loadSegment = async (seg) => {
    if (!activeStore) return
    const newSeg = activeSeg === seg ? null : seg
    setActiveSeg(newSeg)
    try {
      const custs = await customerApi.list(activeStore.id, { segment: newSeg || undefined, page: 1, page_size: 50 })
      setCustomers(custs.results || [])
    } catch(e) { console.error(e) }
  }

  const filtered = customers.filter(c =>
    !search ||
    (c.email || '').toLowerCase().includes(search.toLowerCase()) ||
    ((c.full_name || '') + ' ' + (c.first_name || '') + ' ' + (c.last_name || '')).toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div style={{ flex: 1 }}>
      <PageHeader title="Customer Analytics" subtitle="RFM Segmentation - Lifetime Value - Retention" />

      {loading ? <Loading /> : (
        <Content>
          <div className="section-title">Overview</div>
          <Grid cols={4} gap={12} minW={isMobile ? 140 : 160} style={{ marginBottom: 20 }}>
            <KPICard label="Total Customers"  value={(analytics?.total_customers || 0).toLocaleString()} accent="var(--brand-grad)" />
            <KPICard label="Avg Lifetime Value" value={`$${Number(analytics?.avg_ltv || 0).toFixed(0)}`} accent="linear-gradient(90deg,#10B981,#0ABFBC)" />
            <KPICard label="Repeat Rate"      value={`${Number(analytics?.repeat_purchase_rate || 0).toFixed(1)}%`} barPct={analytics?.repeat_purchase_rate} barColor="#8B5CF6" accent="linear-gradient(90deg,#8B5CF6,#EC4899)" />
            <KPICard label="New This Month"   value={String(analytics?.new_this_month || 0)} accent="linear-gradient(90deg,#F59E0B,#EF4444)" />
          </Grid>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '280px minmax(0,1fr)', gap: 16, marginBottom: 16 }}>
            {/* RFM Segments sidebar */}
            <div className="card" style={{ padding: '16px 14px' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>RFM Segments</div>
              {analytics?.segments?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: isMobile ? 'row' : 'column', gap: 6, overflowX: isMobile ? 'auto' : 'visible', paddingBottom: isMobile ? 2 : 0 }}>
                  {analytics.segments.map(seg => (
                    <button key={seg.segment} onClick={() => loadSegment(seg.segment)} style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 10px', borderRadius: 10, border: 'none', cursor: 'pointer',
                      minWidth: isMobile ? 180 : 'auto',
                      background: activeSeg === seg.segment
                        ? `${SEG_COLORS[seg.segment] || 'var(--brand-blue)'}14`
                        : 'transparent',
                      outline: activeSeg === seg.segment ? `1px solid ${SEG_COLORS[seg.segment]}44` : '1px solid transparent',
                      transition: 'all 0.14s', textAlign: 'left', width: '100%',
                    }}
                      onMouseEnter={e => { if (activeSeg !== seg.segment) e.currentTarget.style.background = 'var(--bg-surface)' }}
                      onMouseLeave={e => { if (activeSeg !== seg.segment) e.currentTarget.style.background = 'transparent' }}
                    >
                      <span style={{ fontSize: 17, flexShrink: 0 }}>{SEG_ICONS[seg.segment] || '👤'}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{seg.segment}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                          {seg.count} customers · ${Number(seg.avg_ltv || 0).toFixed(0)} avg LTV
                        </div>
                        <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, overflow: 'hidden', marginTop: 5 }}>
                          <div style={{ width: `${Math.min(100, Number(seg.revenue_pct || 0) * 2)}%`, height: '100%', background: SEG_COLORS[seg.segment] || 'var(--brand-blue)', borderRadius: 2 }} />
                        </div>
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text-secondary)', flexShrink: 0 }}>
                        {Number(seg.revenue_pct || 0).toFixed(0)}%
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <EmptyState icon="👥" title="No RFM data" subtitle="Sync customers to compute segments." />
              )}

              {activeSeg && (
                <button onClick={() => loadSegment(null)} style={{
                  marginTop: 12, width: '100%', padding: '7px 0',
                  background: 'transparent', border: '1px solid var(--border)',
                  borderRadius: 8, color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer',
                }}>
                  Clear filter
                </button>
              )}

              {/* At-risk callout */}
              {analytics?.at_risk_count > 0 && (
                <div style={{ marginTop: 14, padding: '12px 12px', background: 'var(--amber-bg)', borderRadius: 10, border: '1px solid rgba(245,158,11,0.3)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                    ⚠ {analytics.at_risk_count} at churn risk
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 10, lineHeight: 1.5 }}>
                    No purchase in 45+ days. Launch a win-back campaign.
                  </div>
                  <button onClick={() => loadSegment('At Risk')} style={{
                    width: '100%', padding: '6px 0', borderRadius: 7,
                    background: 'var(--amber)', color: '#fff',
                    border: 'none', fontSize: 11, fontWeight: 700, cursor: 'pointer',
                  }}>
                    View segment →
                  </button>
                </div>
              )}
            </div>

            {/* Customer table */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
                <SearchInput value={search} onChange={setSearch} placeholder="Search customers..." />
                <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                  {activeSeg ? `${activeSeg}` : 'All'} - {filtered.length} shown
                </span>
              </div>

              {filtered.length === 0
                ? <EmptyState icon="👥" title="No customers found" subtitle="Try a different segment or search term." />
                : isMobile ? (
                  <div style={{ display: 'grid', gap: 10 }}>
                    {filtered.map(c => {
                      const segColor = SEG_COLORS[c.rfm_segment]
                      const name = c.full_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || 'Anonymous'
                      return (
                        <div key={c.id} className="card" style={{ padding: '12px 12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                            <div style={{
                              width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
                              background: segColor ? `${segColor}22` : 'var(--bg-surface)',
                              color: segColor || 'var(--text-muted)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 12, fontWeight: 700,
                            }}>
                              {name[0]?.toUpperCase() || '?'}
                            </div>
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.email}</div>
                            </div>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                            <div style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: '8px 9px' }}>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>Orders</div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{c.orders_count}</div>
                            </div>
                            <div style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: '8px 9px' }}>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>Total Spent</div>
                              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>${Number(c.total_spent || 0).toFixed(0)}</div>
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                            <div>
                              {c.rfm_segment && (
                                <span style={{
                                  display: 'inline-flex', alignItems: 'center', gap: 4,
                                  padding: '3px 8px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                                  background: segColor ? `${segColor}18` : 'var(--bg-surface)',
                                  color: segColor || 'var(--text-secondary)',
                                }}>
                                  {SEG_ICONS[c.rfm_segment]} {c.rfm_segment}
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              {c.last_order_date ? new Date(c.last_order_date).toLocaleDateString() : '-'}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <DataTable headers={['Customer', 'Orders', 'Total Spent', 'Segment', 'Last Order']}>
                    {filtered.map(c => {
                      const segColor = SEG_COLORS[c.rfm_segment]
                      const name = c.full_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || 'Anonymous'
                      return (
                        <TR key={c.id}>
                          <TD>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <div style={{
                                width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
                                background: segColor ? `${segColor}22` : 'var(--bg-surface)',
                                color: segColor || 'var(--text-muted)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 11, fontWeight: 700,
                              }}>
                                {name[0]?.toUpperCase() || '?'}
                              </div>
                              <div>
                                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{name}</div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.email}</div>
                              </div>
                            </div>
                          </TD>
                          <TD mono>{c.orders_count}</TD>
                          <TD mono fw={700}>${Number(c.total_spent || 0).toFixed(0)}</TD>
                          <TD>
                            {c.rfm_segment && (
                              <span style={{
                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                padding: '3px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                                background: segColor ? `${segColor}18` : 'var(--bg-surface)',
                                color: segColor || 'var(--text-secondary)',
                              }}>
                                {SEG_ICONS[c.rfm_segment]} {c.rfm_segment}
                              </span>
                            )}
                          </TD>
                          <TD muted>
                            {c.last_order_date ? new Date(c.last_order_date).toLocaleDateString() : '—'}
                          </TD>
                        </TR>
                      )
                    })}
                  </DataTable>
                )}
            </div>
          </div>
        </Content>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════
   ALERTS
═══════════════════════════════════════════════════════════════════════ */
export function Alerts() {
  const { activeStore } = useStore()
  const [loading, setLoading] = useState(true)
  const [data, setData]       = useState({ summary: {}, alerts: [] })

  const load = useCallback(async () => {
    if (!activeStore) { setLoading(false); return }
    setLoading(true)
    try { setData(await alertsApi.list(activeStore.id)) }
    catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [activeStore])

  useEffect(() => { load() }, [load])

  const resolve = async (alertId) => {
    try {
      await alertsApi.resolve(activeStore.id, alertId)
      setData(d => ({ ...d, alerts: d.alerts.filter(a => a.id !== alertId) }))
    } catch(e) { console.error(e) }
  }

  const critical = data.alerts.filter(a => a.severity === 'critical')
  const warnings = data.alerts.filter(a => a.severity === 'warning')
  const opps     = data.alerts.filter(a => ['success', 'info'].includes(a.severity))

  return (
    <div style={{ flex: 1 }}>
      <PageHeader title="Alerts & Notifications" subtitle={`${data.alerts.length} active alerts`}>
        <button onClick={load} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 8,
          background: 'var(--bg-surface)', border: '1px solid var(--border)',
          color: 'var(--text-secondary)', fontSize: 12, fontWeight: 500, cursor: 'pointer',
        }}>
          <span style={{ display: 'flex', alignItems: 'center' }}>{Icon.sync}</span> Refresh
        </button>
      </PageHeader>

      {loading ? <Loading /> : (
        <Content>
          {data.alerts.length === 0 ? (
            <EmptyState icon="🎉" title="All clear!" subtitle="No active alerts. Everything looks healthy." />
          ) : (
            <>
              {/* Summary cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 28 }}>
                {[
                  ['🚨', 'Critical',     critical.length, 'var(--red)',         'var(--red-bg)',   'linear-gradient(90deg,#EF4444,#F97316)'],
                  ['⚠️', 'Warnings',     warnings.length, 'var(--amber)',       'var(--amber-bg)', 'linear-gradient(90deg,#F59E0B,#EF4444)'],
                  ['🚀', 'Opportunities', opps.length,    'var(--green)',       'var(--green-bg)', 'linear-gradient(90deg,#10B981,#0ABFBC)'],
                ].map(([icon, label, count, color, bg, grad]) => (
                  <div key={label} className="card" style={{ padding: '16px 18px', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: grad, borderRadius: '12px 12px 0 0' }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 22 }}>{icon}</span>
                      <div>
                        <div style={{ fontSize: 26, fontWeight: 800, color, fontFamily: 'var(--mono)', lineHeight: 1 }}>{count}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {critical.length > 0 && (
                <>
                  <div className="section-title">🚨 Critical — Requires immediate action</div>
                  {critical.map(a => <AlertCard key={a.id} alert={a} onResolve={resolve} />)}
                </>
              )}
              {warnings.length > 0 && (
                <>
                  <div className="section-title">⚠️ Warnings</div>
                  {warnings.map(a => <AlertCard key={a.id} alert={a} onResolve={resolve} />)}
                </>
              )}
              {opps.length > 0 && (
                <>
                  <div className="section-title">🚀 Opportunities</div>
                  {opps.map(a => <AlertCard key={a.id} alert={a} onResolve={resolve} />)}
                </>
              )}
            </>
          )}
        </Content>
      )}
    </div>
  )
}
