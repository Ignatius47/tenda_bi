import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { ThemeToggle } from '../components/UI'
import logoSrc from '../assets/logo.png'

function AuthLayout({ children, title, subtitle, switchText, switchLink, switchLabel }) {
  const { theme, toggle } = useTheme()

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      background: 'var(--bg-base)',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute', top: '-20%', right: '-10%',
        width: '500px', height: '500px', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(30,111,217,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '-15%', left: '-5%',
        width: '400px', height: '400px', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(10,191,188,0.04) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Theme toggle — top right */}
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}>
        <ThemeToggle theme={theme} onToggle={toggle} />
      </div>

      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 24px',
      }}>
        <div className="fade-in" style={{ width: '100%', maxWidth: 420 }}>
          {/* Logo */}
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <img src={logoSrc} alt="Tenda Analytics" style={{
              height: 40, objectFit: 'contain',
              filter: theme === 'dark' ? 'brightness(1)' : 'brightness(0.85)',
            }} />
          </div>

          {/* Card */}
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: '32px 32px',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>{title}</h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 28 }}>{subtitle}</p>
            {children}
          </div>

          <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: 'var(--text-muted)' }}>
            {switchText}{' '}
            <Link to={switchLink} style={{ color: 'var(--brand-blue)', fontWeight: 600 }}>{switchLabel}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '10px 12px',
  border: '1px solid var(--border)',
  borderRadius: 9, background: 'var(--bg-input)',
  color: 'var(--text-primary)', fontSize: 14,
  fontFamily: 'var(--font)', outline: 'none',
  transition: 'border-color 0.15s, box-shadow 0.15s',
}

const btnStyle = {
  width: '100%', padding: '11px 0',
  borderRadius: 10, border: 'none',
  background: 'var(--brand-grad)',
  color: '#fff', fontSize: 14, fontWeight: 700,
  cursor: 'pointer', marginTop: 6,
  boxShadow: '0 4px 14px rgba(30,111,217,0.3)',
  transition: 'opacity 0.15s, transform 0.1s',
  letterSpacing: '0.2px',
}

const labelStyle = {
  display: 'flex', flexDirection: 'column', gap: 7,
  fontSize: 12, fontWeight: 600,
  color: 'var(--text-secondary)',
  letterSpacing: '0.3px',
}

export function Login() {
  const { login }   = useAuth()
  const navigate    = useNavigate()
  const [form, setForm]     = useState({ email: '', password: '' })
  const [err, setErr]       = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault(); setErr(''); setLoading(true)
    try { await login(form.email, form.password); navigate('/') }
    catch(ex) { setErr(ex.response?.data?.detail || ex.response?.data?.non_field_errors?.[0] || 'Invalid credentials') }
    finally { setLoading(false) }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your Tenda Analytics account"
      switchText="Don't have an account?" switchLink="/register" switchLabel="Create one free">
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {err && (
          <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13 }}>
            {err}
          </div>
        )}
        <label style={labelStyle}>
          Email address
          <input style={inputStyle} type="email" placeholder="you@company.com"
            value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            required autoFocus
            onFocus={e => { e.target.style.borderColor = 'var(--brand-blue)'; e.target.style.boxShadow = '0 0 0 3px rgba(30,111,217,0.12)' }}
            onBlur={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none' }}
          />
        </label>
        <label style={labelStyle}>
          Password
          <input style={inputStyle} type="password" placeholder="Your password"
            value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            required
            onFocus={e => { e.target.style.borderColor = 'var(--brand-blue)'; e.target.style.boxShadow = '0 0 0 3px rgba(30,111,217,0.12)' }}
            onBlur={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none' }}
          />
        </label>
        <button style={{ ...btnStyle, opacity: loading ? 0.7 : 1 }} type="submit" disabled={loading}
          onMouseEnter={e => !loading && (e.currentTarget.style.opacity = '0.9')}
          onMouseLeave={e => e.currentTarget.style.opacity = loading ? '0.7' : '1'}
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </AuthLayout>
  )
}

export function Register() {
  const { register } = useAuth()
  const navigate     = useNavigate()
  const [form, setForm]       = useState({ full_name: '', email: '', password: '' })
  const [err, setErr]         = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async e => {
    e.preventDefault(); setErr('')
    if (form.password.length < 8) { setErr('Password must be at least 8 characters'); return }
    setLoading(true)
    try { await register(form.email, form.password, form.full_name); navigate('/onboarding') }
    catch(ex) { setErr(ex.response?.data?.email?.[0] || ex.response?.data?.detail || 'Registration failed') }
    finally { setLoading(false) }
  }

  const fields = [
    { key: 'full_name', label: 'Full name',     type: 'text',     placeholder: 'Jane Muthoni',      required: false },
    { key: 'email',     label: 'Email address', type: 'email',    placeholder: 'you@company.com',    required: true },
    { key: 'password',  label: 'Password',      type: 'password', placeholder: 'Min. 8 characters',  required: true },
  ]

  return (
    <AuthLayout title="Create your account" subtitle="Start turning your Shopify data into decisions"
      switchText="Already have an account?" switchLink="/login" switchLabel="Sign in">
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        {err && (
          <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13 }}>
            {err}
          </div>
        )}
        {fields.map(f => (
          <label key={f.key} style={labelStyle}>
            {f.label}
            <input style={inputStyle} type={f.type} placeholder={f.placeholder}
              value={form[f.key]} onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
              required={f.required}
              onFocus={e => { e.target.style.borderColor = 'var(--brand-blue)'; e.target.style.boxShadow = '0 0 0 3px rgba(30,111,217,0.12)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none' }}
            />
          </label>
        ))}
        <button style={{ ...btnStyle, opacity: loading ? 0.7 : 1 }} type="submit" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}

export default Login
