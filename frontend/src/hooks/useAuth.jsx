import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../api/client'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('tenda_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      api.get('/auth/me/')
        .then(r => setUser(r.data.user))
        .catch(() => {
          localStorage.removeItem('tenda_token')
          delete api.defaults.headers.common['Authorization']
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const _save = (access) => {
    localStorage.setItem('tenda_token', access)
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`
  }

  // Manual email + password login
  const login = async (email, password) => {
    const data = await api.post('/auth/login/', { email, password }).then(r => r.data)
    _save(data.access)
    setUser(data.user)
    return data.user
  }

  const register = async (email, password, full_name) => {
    const data = await api.post('/auth/register/', { email, password, full_name }).then(r => r.data)
    _save(data.access)
    setUser(data.user)
    return data.user
  }

  /**
   * loginWithTokens — called after Shopify OAuth returns JWT in URL params.
   * No email/password needed. Just store the token and fetch the user.
   */
  const loginWithTokens = async (access, refresh) => {
    _save(access)
    if (refresh) localStorage.setItem('tenda_refresh', refresh)
    const data = await api.get('/auth/me/').then(r => r.data)
    setUser(data.user)
    return data.user
  }

  const logout = () => {
    localStorage.removeItem('tenda_token')
    localStorage.removeItem('tenda_refresh')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
  }

  return (
    <Ctx.Provider value={{ user, loading, login, register, loginWithTokens, logout }}>
      {children}
    </Ctx.Provider>
  )
}

export const useAuth = () => useContext(Ctx)