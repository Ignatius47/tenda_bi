import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useTheme } from '../hooks/useTheme'
import logoSrc from '../assets/logo.png'

export default function Onboarding() {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [shop, setShop]         = useState('')
  const [err, setErr]           = useState('')
  const [loading, setLoading]   = useState(false)
  const [step, setStep]         = useState(0) // 0=connect, 1=syncing

  const connect = async e => {
    e.preventDefault(); setErr(''); setLoading(true)
    try {
      let domain = shop.trim().toLowerCase()
      if (!domain.includes('.')) domain = `${domain}.myshopify.com`
      const { redirect_url } = await api.get('/shopify/connect/', { params: { shop: domain } }).then(r => r.data)
      window.location.href = redirect_url
    } catch(ex) {
      setErr(ex.response?.data?.error || 'Connection failed. Check your store URL.')
      setLoading(false)
    }
  }

  const STEPS = ['Connect', 'Import', 'Explore']

  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '40px 24px', background: 'var(--bg-base)', minHeight: '100%',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Decorative blobs */}
      <div style={{ position: 'absolute', top: '-10%', right: '5%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(30,111,217,0.05) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', left: '0%', width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(circle, rgba(10,191,188,0.04) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div className="fade-in" style={{ width: '100%', maxWidth: 500 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <img src={logoSrc} alt="Tenda Analytics" style={{
            height: 38, objectFit: 'contain',
            filter: theme === 'dark' ? 'brightness(1)' : 'brightness(0.85)',
          }} />
        </div>

        {/* Steps indicator */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 32, gap: 0 }}>
          {STEPS.map((s, i) => (
            <React.Fragment key={s}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: '50%',
                  background: i <= step
                    ? 'var(--brand-grad)'
                    : 'var(--bg-surface)',
                  border: `1px solid ${i <= step ? 'transparent' : 'var(--border)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 700,
                  color: i <= step ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.3s',
                  boxShadow: i === step ? '0 4px 12px rgba(30,111,217,0.3)' : 'none',
                }}>
                  {i < step ? '✓' : i + 1}
                </div>
                <span style={{
                  fontSize: 11, fontWeight: i === step ? 600 : 400,
                  color: i === step ? 'var(--text-primary)' : 'var(--text-muted)',
                }}>{s}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{
                  height: 1, width: 72,
                  background: i < step ? 'var(--brand-blue)' : 'var(--border)',
                  margin: '0 8px', marginBottom: 22,
                  transition: 'background 0.3s',
                }} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 16, padding: '32px 32px',
          boxShadow: 'var(--shadow-lg)',
        }}>
          {step === 0 && (
            <>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🛍️</div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                Connect your Shopify store
              </h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.7 }}>
                Enter your store URL to connect via Shopify OAuth. We only request read permissions — your data stays yours.
              </p>

              <form onSubmit={connect} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                {err && (
                  <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13 }}>
                    {err}
                  </div>
                )}

                <label style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.3px' }}>
                  Shopify store URL
                  <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 9, overflow: 'hidden', background: 'var(--bg-input)', transition: 'border-color 0.15s' }}
                    onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--brand-blue)'}
                    onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    <input type="text" placeholder="your-store" value={shop}
                      onChange={e => setShop(e.target.value)} required autoFocus
                      style={{ flex: 1, padding: '10px 12px', background: 'transparent', border: 'none', outline: 'none', fontSize: 14, color: 'var(--text-primary)', fontFamily: 'var(--font)' }}
                    />
                    <span style={{ padding: '10px 14px', fontSize: 13, color: 'var(--text-muted)', borderLeft: '1px solid var(--border)', display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', background: 'var(--bg-surface)' }}>
                      .myshopify.com
                    </span>
                  </div>
                </label>

                <button type="submit" disabled={loading} style={{
                  padding: '12px 0', borderRadius: 10, border: 'none',
                  background: 'var(--brand-grad)', color: '#fff',
                  fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.7 : 1,
                  boxShadow: '0 4px 14px rgba(30,111,217,0.3)',
                  transition: 'opacity 0.15s',
                }}>
                  {loading ? 'Redirecting to Shopify…' : 'Connect store →'}
                </button>
              </form>

              <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                <span>🔒</span>
                <span>Secured via Shopify OAuth · Read-only permissions · No passwords stored</span>
              </div>

              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <button onClick={() => navigate('/')} style={{
                  background: 'none', border: 'none', color: 'var(--text-muted)',
                  fontSize: 12, cursor: 'pointer', textDecoration: 'underline',
                }}>
                  Skip — explore the dashboard first
                </button>
              </div>
            </>
          )}

          {step === 1 && (
            <div style={{ textAlign: 'center', padding: '12px 0' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>⚡</div>
              <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10, color: 'var(--text-primary)' }}>Importing your data</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.7 }}>
                We're pulling your orders, products, customers, and inventory from Shopify. Large stores take 2–3 minutes.
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 28 }}>
                <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>
                You can leave this page — sync continues in the background.
              </p>
              <button onClick={() => navigate('/')} style={{
                padding: '11px 28px', borderRadius: 10,
                background: 'var(--brand-grad)', color: '#fff',
                border: 'none', fontSize: 13, fontWeight: 700, cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(30,111,217,0.3)',
              }}>
                Go to dashboard →
              </button>
            </div>
          )}
        </div>

        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
          Setup takes under 5 minutes · No code required
        </p>
      </div>
    </div>
  )
}
