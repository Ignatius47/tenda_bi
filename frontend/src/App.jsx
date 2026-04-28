import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider }  from './hooks/useTheme'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { StoreProvider } from './hooks/useStore'
import AppLayout         from './components/AppLayout'

// Pages
import ConnectPage       from './pages/ConnectPage'
import ShopifySuccess    from './pages/ShopifySuccess'
import Dashboard         from './pages/Dashboard'
import Products          from './pages/Products'
import Inventory         from './pages/Inventory'
import Customers         from './pages/Customers'
import Alerts            from './pages/Alerts'

/**
 * Route guards
 */
function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 12, background: 'var(--bg-base)' }}>
      <div className="spinner" style={{ width: 28, height: 28 }} />
      <span style={{ color: 'var(--text-3)', fontSize: 13 }}>Loading…</span>
    </div>
  )
  return user ? children : <Navigate to="/connect" replace />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return !user ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <StoreProvider>
          <BrowserRouter>
            <Routes>

              {/* ── Public routes ──────────────────────────────────────── */}

              {/* Shopify-first connect page (new entry point) */}
              <Route path="/connect" element={
                <PublicRoute><ConnectPage /></PublicRoute>
              } />

              {/* OAuth return — shows loading screen, reads JWT from URL */}
              {/* Not wrapped in PublicRoute because the user IS being logged in here */}
              <Route path="/auth/shopify/success" element={<ShopifySuccess />} />

              {/* Legacy redirects — old /login and /register now go to /connect */}
              <Route path="/login"    element={<Navigate to="/connect" replace />} />
              <Route path="/register" element={<Navigate to="/connect" replace />} />

              {/* ── Protected app routes ───────────────────────────────── */}
              <Route path="/" element={
                <PrivateRoute><AppLayout /></PrivateRoute>
              }>
                <Route index             element={<Dashboard />} />
                <Route path="products"   element={<Products />} />
                <Route path="inventory"  element={<Inventory />} />
                <Route path="customers"  element={<Customers />} />
                <Route path="alerts"     element={<Alerts />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/" replace />} />

            </Routes>
          </BrowserRouter>
        </StoreProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}