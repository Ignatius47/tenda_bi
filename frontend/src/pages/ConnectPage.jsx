import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { ThemeToggle } from '../components/UI'
import logoSrc from '../assets/logo.png'

/**
 * ConnectPage — the main entry point for new users.
 *
 * Flow:
 *   1. User types their store URL and clicks "Connect Shopify"
 *   2. Browser redirects to /api/auth/shopify/start/?shop=xxx
 *   3. Backend redirects to Shopify OAuth
 *   4. User approves on Shopify
 *   5. Shopify redirects to /api/auth/shopify/callback/
 *   6. Backend creates account + issues JWT
 *   7. Backend redirects to /auth/shopify/success?access=...
 *   8. ShopifySuccess.jsx reads token + shows loading screen + goes to dashboard
 *
 * No email, no password, no forms — Shopify is the identity provider.
 * A small "sign in with email" toggle is available for admin/analyst accounts.
 */
export default function ConnectPage() {
  const { loginWithTokens, login } = useAuth()
  const { theme, toggle }          = useTheme()
  const navigate                   = useNavigate()
  const [params]                   = useSearchParams()

  const [shop, setShop]           = useState('')
  const [err, setErr]             = useState('')
  const [showEmail, setShowEmail] = useState(false)
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [loading, setLoading]     = useState(false)

  // Handle error param from backend (e.g. HMAC failed)
  useEffect(() => {
    const error = params.get('error')
    if (error === 'hmac_failed') setErr('Shopify verification failed. Please try again.')
    if (error === 'token_failed') setErr('Could not connect to Shopify. Please try again.')
  }, [params])

  const connectShopify = (e) => {
    e.preventDefault()
    setErr('')
    let domain = shop.trim().toLowerCase()
    if (!domain) { setErr('Enter your store URL'); return }
    if (!domain.includes('.')) domain = `${domain}.myshopify.com`
    // Redirect browser directly to backend OAuth start endpoint
    window.location.href = `/api/auth/shopify/start/?shop=${encodeURIComponent(domain)}`
  }

  const emailLogin = async (e) => {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch(ex) {
      setErr(
        ex.response?.data?.non_field_errors?.[0] ||
        ex.response?.data?.detail ||
        'Invalid credentials'
      )
    } finally {
      setLoading(false)
    }
  }

  const inp = {
    width: '100%', padding: '11px 14px',
    border: '1px solid var(--border)', borderRadius: 10,
    background: 'var(--bg-input)', color: 'var(--text-1)',
    fontSize: 14, fontFamily: 'var(--font)', outline: 'none',
    transition: 'border-color .15s',
  }

  return (
    <div className="connect-page" style={{
      minHeight: '100vh', display: 'flex',
      background: 'var(--bg-base)',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Background blobs */}
      <div style={{ position: 'absolute', top: '-15%', right: '-5%', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle,rgba(30,111,217,.06) 0%,transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', left: '-5%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle,rgba(10,191,188,.04) 0%,transparent 70%)', pointerEvents: 'none' }} />

      {/* Theme toggle */}
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}>
        <ThemeToggle theme={theme} onToggle={toggle} />
      </div>

      <div className="connect-shell" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px' }}>
        <div className="fade-in" style={{ width: '100%', maxWidth: 440 }}>

          {/* Logo */}
          <div className="connect-logo-wrap" style={{ textAlign: 'center', marginBottom: 36 }}>
            <img src={logoSrc} alt="Tenda Analytics"
              className="connect-logo"
              style={{ height: 40, objectFit: 'contain', filter: theme === 'dark' ? 'none' : 'brightness(.85)' }} />
          </div>

          {/* Card */}
          <div className="connect-card" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 16, padding: '32px', boxShadow: 'var(--shadow-lg)' }}>

            {!showEmail ? (
              <>
                {/* Hero */}
                <div className="connect-hero" style={{ textAlign: 'center', marginBottom: 28 }}>
                  <div className="connect-title" style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 8, lineHeight: 1.3 }}>
                    Your store intelligence,<br />in one place.
                  </div>
                  <div className="connect-subtitle" style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7 }}>
                    Connect your Shopify store for instant analytics, inventory alerts, and AI insights. No forms. No setup.
                  </div>
                </div>

                {/* Feature pills */}
                <div className="connect-pills" style={{ display: 'flex', flexWrap: 'wrap', gap: 7, justifyContent: 'center', marginBottom: 28 }}>
                  {['Revenue trends', 'RFM segments', 'Stock alerts', 'AI insights'].map(f => (
                    <span key={f} className="connect-pill" style={{ padding: '4px 12px', borderRadius: 20, background: 'var(--blue-bg)', color: 'var(--brand-blue)', fontSize: 12, fontWeight: 500 }}>
                      {f}
                    </span>
                  ))}
                </div>

                {/* Shopify connect form */}
                <form onSubmit={connectShopify}>
                  {err && (
                    <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13, marginBottom: 16 }}>
                      {err}
                    </div>
                  )}

                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-2)', letterSpacing: '.3px', marginBottom: 7 }}>
                    Shopify store URL
                  </div>

                  <div className="connect-domain-wrap" style={{
                    display: 'flex', border: '1px solid var(--border)',
                    borderRadius: 10, overflow: 'hidden',
                    background: 'var(--bg-input)', marginBottom: 16,
                    transition: 'border-color .15s',
                  }}
                    onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--brand-blue)'}
                    onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    <input className="connect-domain-input" type="text" placeholder="your-store" value={shop}
                      onChange={e => setShop(e.target.value)} autoFocus
                      style={{ flex: 1, padding: '12px 14px', background: 'transparent', border: 'none', outline: 'none', fontSize: 14, color: 'var(--text-1)', fontFamily: 'var(--font)' }}
                    />
                    <span className="connect-domain-suffix" style={{ padding: '12px 14px', fontSize: 13, color: 'var(--text-3)', borderLeft: '1px solid var(--border)', background: 'var(--bg-surface)', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
                      .myshopify.com
                    </span>
                  </div>

                  <button className="connect-cta" type="submit" style={{
                    width: '100%', padding: '13px 0', borderRadius: 10, border: 'none',
                    background: 'var(--brand-grad)', color: '#fff',
                    fontSize: 15, fontWeight: 700, cursor: 'pointer',
                    boxShadow: '0 4px 20px rgba(30,111,217,.35)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                    transition: 'opacity .15s, transform .1s',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.opacity = '.9'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                    onMouseLeave={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'none' }}
                  >
                    {/* Shopify bag icon */}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white" style={{ flexShrink: 0 }}>
                      <path d="M20.5 7.5h-2.4C17.7 4.5 15.1 2.5 12 2.5S6.3 4.5 5.9 7.5H3.5C2.7 7.5 2 8.2 2 9v11c0 .8.7 1.5 1.5 1.5h17c.8 0 1.5-.7 1.5-1.5V9c0-.8-.7-1.5-1.5-1.5zM12 4.5c2 0 3.7 1.3 4.2 3H7.8c.5-1.7 2.2-3 4.2-3zm0 10c-1.7 0-3-1.3-3-3s1.3-3 3-3 3 1.3 3 3-1.3 3-3 3z"/>
                    </svg>
                    Connect Shopify store
                  </button>
                </form>

                <div className="connect-security" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, fontSize: 12, color: 'var(--text-3)' }}>
                  <span>🔒</span>
                  <span>Secured via Shopify OAuth · Read-only access · No passwords stored</span>
                </div>

                <div style={{ textAlign: 'center', marginTop: 20, paddingTop: 18, borderTop: '1px solid var(--border)' }}>
                  <button onClick={() => { setShowEmail(true); setErr('') }}
                    style={{ background: 'none', border: 'none', color: 'var(--text-3)', fontSize: 12, cursor: 'pointer' }}>
                    Sign in with email instead →
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-1)', marginBottom: 6 }}>Sign in</h2>
                <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 24 }}>For admin and analyst accounts.</p>

                <form onSubmit={emailLogin} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {err && (
                    <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13 }}>
                      {err}
                    </div>
                  )}
                  <label style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 12, fontWeight: 600, color: 'var(--text-2)' }}>
                    Email address
                    <input style={inp} type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@company.com"
                      onFocus={e => e.target.style.borderColor = 'var(--brand-blue)'}
                      onBlur={e => e.target.style.borderColor = 'var(--border)'} />
                  </label>
                  <label style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 12, fontWeight: 600, color: 'var(--text-2)' }}>
                    Password
                    <input style={inp} type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Your password"
                      onFocus={e => e.target.style.borderColor = 'var(--brand-blue)'}
                      onBlur={e => e.target.style.borderColor = 'var(--border)'} />
                  </label>
                  <button type="submit" disabled={loading} style={{
                    padding: '12px 0', borderRadius: 10, border: 'none',
                    background: 'var(--brand-grad)', color: '#fff',
                    fontSize: 14, fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? .7 : 1,
                    boxShadow: '0 4px 14px rgba(30,111,217,.3)',
                  }}>
                    {loading ? 'Signing in…' : 'Sign in'}
                  </button>
                </form>

                <div style={{ textAlign: 'center', marginTop: 18 }}>
                  <button onClick={() => { setShowEmail(false); setErr('') }}
                    style={{ background: 'none', border: 'none', color: 'var(--text-3)', fontSize: 12, cursor: 'pointer' }}>
                    ← Back to Shopify connect
                  </button>
                </div>
              </>
            )}
          </div>

          <p className="connect-footnote" style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'var(--text-3)' }}>
            No credit card required · Works with any Shopify store
          </p>
        </div>
      </div>
    </div>
  )
}
