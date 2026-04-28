import React, { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useStore } from '../hooks/useStore'
import { useTheme } from '../hooks/useTheme'
import { Icon, ThemeToggle } from './UI'
import logoSrc from '../assets/logo.png'
import faviconSrc from '../assets/favicon.png'

const NAV = [
  { to: '/',          label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/products',  label: 'Products',  icon: 'products' },
  { to: '/inventory', label: 'Inventory', icon: 'inventory' },
  { to: '/customers', label: 'Customers', icon: 'customers' },
  { to: '/alerts',    label: 'Alerts',    icon: 'alerts',   badge: true },
]

export default function AppLayout() {
  const { user, logout }                                  = useAuth()
  const { stores, activeStore, selectStore, triggerSync } = useStore()
  const { theme, toggle }                                 = useTheme()
  const navigate                                          = useNavigate()
  const location                                          = useLocation()

  const [collapsed, setCollapsed]   = useState(() => localStorage.getItem('sidebar_collapsed') === 'true')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [syncing, setSyncing]       = useState(false)
  const [showStores, setShowStores] = useState(false)
  const [isMobile, setIsMobile]     = useState(window.innerWidth < 768)
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    const onResize = () => {
      const m = window.innerWidth < 768
      setIsMobile(m)
      if (!m) setMobileOpen(false)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(collapsed))
  }, [collapsed])

  useEffect(() => {
    if (!activeStore) return
    import('../api/client').then(m => {
      m.alertsApi.list(activeStore.id)
        .then(d => setAlertCount(d.summary?.critical || 0))
        .catch(() => {})
    })
  }, [activeStore])

  const handleSync = async () => {
    setSyncing(true)
    try { await triggerSync() } finally { setSyncing(false) }
  }

  const sw = collapsed ? '64px' : '256px'

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div onClick={() => setMobileOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.65)', backdropFilter: 'blur(3px)', zIndex: 90 }} />
      )}

      {/* ── Desktop Sidebar ───────────────────────────────────────────────── */}
      {!isMobile && (
        <aside style={{
          width: sw, minWidth: sw,
          background: 'var(--bg-card)',
          borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column',
          transition: 'width .25s cubic-bezier(.4,0,.2,1), min-width .25s cubic-bezier(.4,0,.2,1)',
          overflow: 'hidden', flexShrink: 0, zIndex: 100,
        }}>

          {/* Logo */}
          <div style={{ height: 60, display: 'flex', alignItems: 'center', padding: collapsed ? '0 14px' : '0 16px', borderBottom: '1px solid var(--border)', flexShrink: 0, justifyContent: collapsed ? 'center' : 'space-between' }}>
            <img src={collapsed ? faviconSrc : logoSrc} alt="Tenda Analytics"
              style={{ height: collapsed ? 30 : 34, maxWidth: collapsed ? 30 : 160, objectFit: 'contain', filter: theme === 'dark' ? 'none' : 'brightness(.85)' }} />
            <button onClick={() => setCollapsed(c => !c)} title={collapsed ? 'Expand' : 'Collapse'}
              style={{ width: 26, height: 26, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-3)', cursor: 'pointer', flexShrink: 0 }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              {collapsed ? Icon.chevronR : Icon.chevronL}
            </button>
          </div>

          {/* Store switcher */}
          {!collapsed && (
            <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
              <button onClick={() => setShowStores(v => !v)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 9, background: 'var(--bg-elevated)', border: '1px solid var(--border-s, rgba(255,255,255,.13))', cursor: 'pointer', textAlign: 'left', color: 'var(--text-1)' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--brand-blue)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-s, rgba(255,255,255,.13))'}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: activeStore ? 'var(--green)' : 'var(--amber)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {activeStore ? (activeStore.shop_name || activeStore.shop_domain) : 'No store connected'}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-2)', marginTop: 2 }}>
                    {activeStore?.last_synced_at
                      ? `Synced - ${new Date(activeStore.last_synced_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · ${new Date(activeStore.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                      : 'Not synced'}
                  </div>
                </div>
                <span style={{ color: 'var(--text-2)', fontSize: 10 }}>{showStores ? '▲' : '▾'}</span>
              </button>

              {showStores && (
                <div style={{ marginTop: 4, background: 'var(--bg-elevated)', border: '1px solid var(--border-s, rgba(255,255,255,.13))', borderRadius: 9, overflow: 'hidden' }}>
                  {stores.map(s => (
                    <button key={s.id} onClick={() => { selectStore(s); setShowStores(false) }}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <div style={{ fontSize: 12, color: 'var(--text-1)', flex: 1 }}>{s.shop_name || s.shop_domain}</div>
                      {activeStore?.id === s.id && <span style={{ color: 'var(--green)' }}>{Icon.check}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Collapsed store dot */}
          {collapsed && (
            <div style={{ padding: 10, display: 'flex', justifyContent: 'center', borderBottom: '1px solid var(--border)' }}>
              <div style={{ width: 36, height: 36, borderRadius: 9, background: 'var(--bg-surface)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-2)' }}>
                {Icon.store}
              </div>
            </div>
          )}

          {/* Nav */}
          <nav style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
            {!collapsed && <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '1px', padding: '6px 8px 4px' }}>Analytics</div>}

            {NAV.map(item => (
              <NavLink key={item.to} to={item.to} end={item.end}
                style={({ isActive }) => ({
                  display: 'flex', alignItems: 'center',
                  gap: collapsed ? 0 : 10,
                  padding: collapsed ? 10 : '9px 10px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  borderRadius: 9, textDecoration: 'none', marginBottom: 2, position: 'relative',
                  background: isActive ? 'rgba(30,111,217,.12)' : 'transparent',
                  color: isActive ? 'var(--brand-blue)' : 'var(--text-2)',
                  fontWeight: isActive ? 600 : 400, fontSize: 13,
                })}>
                {({ isActive }) => (
                  <>
                    {isActive && <div style={{ position: 'absolute', left: 0, top: '20%', bottom: '20%', width: 3, borderRadius: '0 2px 2px 0', background: 'var(--brand-blue)' }} />}
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, position: 'relative', color: isActive ? 'var(--brand-blue)' : 'var(--text-2)' }}>
                      {Icon[item.icon]}
                      {item.badge && alertCount > 0 && (
                        <span style={{ position: 'absolute', top: -4, right: -5, width: 15, height: 15, borderRadius: '50%', background: 'var(--red)', color: '#fff', fontSize: 8, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {alertCount > 9 ? '9+' : alertCount}
                        </span>
                      )}
                    </span>
                    {!collapsed && (
                      <>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</span>
                        {item.badge && alertCount > 0 && (
                          <span style={{ marginLeft: 'auto', background: 'var(--red)', color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 10 }}>{alertCount}</span>
                        )}
                      </>
                    )}
                  </>
                )}
              </NavLink>
            ))}

            <div style={{ borderTop: '1px solid var(--border)', marginTop: 8, paddingTop: 8 }}>
              {!collapsed && <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '1px', padding: '4px 8px' }}>Store</div>}
              <button onClick={handleSync} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: collapsed ? 0 : 10, justifyContent: collapsed ? 'center' : 'flex-start', padding: collapsed ? 10 : '9px 10px', borderRadius: 9, background: 'transparent', border: 'none', color: 'var(--text-2)', fontSize: 13, cursor: 'pointer' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-surface)'; e.currentTarget.style.color = 'var(--text-1)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-2)' }}>
                <span style={{ display: 'flex', animation: syncing ? 'spin 1s linear infinite' : 'none' }}>{Icon.sync}</span>
                {!collapsed && <span>{syncing ? 'Syncing…' : 'Sync Now'}</span>}
              </button>
            </div>
          </nav>

          {/* User row */}
          <div style={{ borderTop: '1px solid var(--border)', padding: collapsed ? '12px 10px' : '12px 14px', flexShrink: 0 }}>
            {collapsed ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--brand-grad)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#fff' }}>
                  {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                </div>
                <button onClick={logout} style={{ width: 32, height: 32, borderRadius: 8, border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {Icon.logout}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--brand-grad)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#fff', flexShrink: 0 }}>
                  {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.full_name || 'Account'}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.email}</div>
                </div>
                <button onClick={logout} style={{ width: 28, height: 28, borderRadius: 7, border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}>
                  {Icon.logout}
                </button>
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

        {/* Desktop topbar */}
        {!isMobile && (
          <header style={{ height: 60, display: 'flex', alignItems: 'center', gap: 12, padding: '0 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-card)', flexShrink: 0, zIndex: 20 }}>
            <div style={{ flex: 1 }} />
            <ThemeToggle theme={theme} onToggle={toggle} />
          </header>
        )}

        {/* Mobile topbar — logo centered, theme toggle right, no hamburger */}
        {isMobile && (
          <header style={{
            height: 56, display: 'flex', alignItems: 'center',
            padding: '0 16px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--bg-card)',
            flexShrink: 0, zIndex: 20,
            position: 'relative',
          }}>
            {/* Logo centered */}
            <div style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}>
              <img src={logoSrc} alt="Tenda Analytics"
                style={{ height: 28, objectFit: 'contain', filter: theme === 'dark' ? 'none' : 'brightness(.85)', display: 'block' }} />
            </div>
            {/* Theme toggle right */}
            <div style={{ marginLeft: 'auto' }}>
              <ThemeToggle theme={theme} onToggle={toggle} />
            </div>
          </header>
        )}

        {/* Page content */}
        <main style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-base)', paddingBottom: isMobile ? 'calc(76px + env(safe-area-inset-bottom, 0px))' : 0 }}>
          <Outlet context={{ isMobile }} />
        </main>

        {/* Mobile bottom nav */}
        {isMobile && (
          <nav style={{
            position: 'fixed', bottom: 0, left: 0, right: 0,
            height: 68, background: 'var(--bg-card)',
            borderTop: '1px solid var(--border)',
            display: 'flex', zIndex: 100,
            paddingBottom: 'env(safe-area-inset-bottom, 0px)',
          }}>
            {NAV.map(item => (
              <NavLink key={item.to} to={item.to} end={item.end}
                style={({ isActive }) => ({
                  flex: 1, display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  gap: 4, textDecoration: 'none',
                  fontSize: 10, fontWeight: isActive ? 600 : 400,
                  color: isActive ? 'var(--brand-blue)' : 'var(--text-3)',
                  padding: '8px 4px', position: 'relative',
                })}>
                {({ isActive }) => (
                  <>
                    {isActive && <div style={{ position: 'absolute', top: 0, left: '20%', right: '20%', height: 2, background: 'var(--brand-blue)', borderRadius: '0 0 3px 3px' }} />}
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                      {Icon[item.icon]}
                      {item.badge && alertCount > 0 && (
                        <span style={{ position: 'absolute', top: -5, right: -7, width: 15, height: 15, borderRadius: '50%', background: 'var(--red)', color: '#fff', fontSize: 8, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {alertCount > 9 ? '9+' : alertCount}
                        </span>
                      )}
                    </span>
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        )}
      </div>
    </div>
  )
}
