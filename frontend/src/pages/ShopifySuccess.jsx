import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import logoSrc from '../assets/logo.png'

/**
 * ShopifySuccess — shown after Shopify OAuth redirects back to the frontend.
 *
 * URL format: /auth/shopify/success?access=JWT&refresh=JWT&store_id=1&shop_name=X&is_new=true
 *
 * What it does:
 *  1. Reads JWT tokens from URL params
 *  2. Saves them via loginWithTokens()
 *  3. Shows an animated progress screen while the store syncs in background
 *  4. Automatically redirects to dashboard after ~7 seconds
 */

const STEPS = [
  { icon: '🔌', label: 'Connecting to Shopify',      ms: 700  },
  { icon: '📦', label: 'Importing your products',    ms: 1600 },
  { icon: '🛒', label: 'Pulling order history',      ms: 2700 },
  { icon: '👥', label: 'Analysing your customers',   ms: 3800 },
  { icon: '📊', label: 'Computing revenue metrics',  ms: 4900 },
  { icon: '🤖', label: 'Generating AI insights',     ms: 5900 },
  { icon: '✅', label: 'Your dashboard is ready!',   ms: 6700 },
]

export default function ShopifySuccess() {
  const { loginWithTokens } = useAuth()
  const { theme }           = useTheme()
  const navigate            = useNavigate()
  const [params]            = useSearchParams()
  const [stepIdx, setStepIdx] = useState(0)
  const [done, setDone]       = useState(false)
  const [err, setErr]         = useState('')

  const shopName = params.get('shop_name') || 'Your store'

  // Save tokens as soon as we land here
  useEffect(() => {
    const access  = params.get('access')
    const refresh = params.get('refresh')

    if (!access) {
      // No token — something went wrong, send back to connect
      navigate('/connect?error=no_token', { replace: true })
      return
    }

    loginWithTokens(access, refresh).catch(() => {
      setErr('Login failed. Please try connecting again.')
    })
  }, [])

  // Progress animation — independent of the actual sync
  // The sync happens in the background on the server
  useEffect(() => {
    const timers = STEPS.map((s, i) =>
      setTimeout(() => {
        setStepIdx(i)
        if (i === STEPS.length - 1) {
          setDone(true)
          setTimeout(() => navigate('/', { replace: true }), 1500)
        }
      }, s.ms)
    )
    return () => timers.forEach(clearTimeout)
  }, [])

  if (err) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-base)', flexDirection: 'column', gap: 16, padding: 24, textAlign: 'center' }}>
      <div style={{ fontSize: 48 }}>❌</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)' }}>Connection failed</div>
      <div style={{ fontSize: 13, color: 'var(--text-3)', maxWidth: 320 }}>{err}</div>
      <button onClick={() => navigate('/connect')} style={{ padding: '10px 24px', borderRadius: 10, background: 'var(--brand-grad)', color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer', marginTop: 8 }}>
        Try again
      </button>
    </div>
  )

  const current = STEPS[stepIdx]
  const pct     = Math.round(((stepIdx + 1) / STEPS.length) * 100)

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-base)', padding: 24,
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{ position: 'absolute', top: '-20%', right: '-10%', width: 600, height: 600, borderRadius: '50%', background: 'radial-gradient(circle,rgba(30,111,217,.07) 0%,transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-15%', left: '-5%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle,rgba(10,191,188,.05) 0%,transparent 70%)', pointerEvents: 'none' }} />

      <div className="fade-in" style={{ width: '100%', maxWidth: 440, textAlign: 'center' }}>
        {/* Logo */}
        <img src={logoSrc} alt="Tenda Analytics"
          style={{ height: 36, objectFit: 'contain', marginBottom: 40, filter: theme === 'dark' ? 'none' : 'brightness(.85)' }} />

        {/* Animated icon */}
        <div key={stepIdx} className="fade-in" style={{ fontSize: 60, marginBottom: 20, lineHeight: 1 }}>
          {current.icon}
        </div>

        {/* Heading */}
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 10 }}>
          {done
            ? `Welcome${shopName !== 'Your store' ? `, ${shopName.split(' ')[0]}` : ''}! 🎉`
            : 'Setting up your analytics…'
          }
        </div>

        {/* Step label */}
        <div key={`label-${stepIdx}`} className="fade-in" style={{ fontSize: 14, color: 'var(--text-2)', marginBottom: 32, minHeight: 22 }}>
          {current.label}
        </div>

        {/* Progress bar */}
        <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden', marginBottom: 10 }}>
          <div style={{
            height: '100%', background: 'var(--brand-grad)',
            borderRadius: 3, width: `${pct}%`,
            transition: 'width .6s cubic-bezier(.4,0,.2,1)',
          }} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 40 }}>
          {pct}% complete
        </div>

        {/* Step indicator dots */}
        <div style={{ display: 'flex', gap: 5, justifyContent: 'center', marginBottom: 40 }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              height: 5, borderRadius: 3,
              width: i === stepIdx ? 22 : 5,
              background: i <= stepIdx ? 'var(--brand-blue)' : 'var(--border)',
              transition: 'all .4s cubic-bezier(.4,0,.2,1)',
            }} />
          ))}
        </div>

        {!done && (
          <div style={{ fontSize: 12, color: 'var(--text-3)', lineHeight: 1.6 }}>
            Your data is syncing in the background.<br />
            Large stores with many orders take 1–2 minutes to fully import.
          </div>
        )}

        {done && (
          <button onClick={() => navigate('/', { replace: true })} style={{
            padding: '12px 32px', borderRadius: 10,
            background: 'var(--brand-grad)', color: '#fff',
            border: 'none', fontSize: 14, fontWeight: 700,
            cursor: 'pointer', boxShadow: '0 4px 20px rgba(30,111,217,.35)',
          }}>
            Go to dashboard →
          </button>
        )}
      </div>
    </div>
  )
}