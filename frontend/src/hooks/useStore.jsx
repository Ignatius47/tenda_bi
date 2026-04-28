import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../api/client'
import { useAuth } from './useAuth'

const Ctx = createContext(null)

export function StoreProvider({ children }) {
  const { user } = useAuth()
  const [stores, setStores]           = useState([])
  const [activeStore, setActiveStore] = useState(null)
  const [loading, setLoading]         = useState(false)

  useEffect(() => { if (user) fetchStores() }, [user])

  const fetchStores = async () => {
    setLoading(true)
    try {
      const list = await api.get('/shopify/stores/').then(r => r.data)
      setStores(list)
      if (list.length && !activeStore) {
        const saved = localStorage.getItem('tenda_active_store')
        const found = saved ? list.find(s => s.id === parseInt(saved)) : null
        setActiveStore(found || list[0])
      }
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }

  const selectStore = (store) => {
    setActiveStore(store)
    localStorage.setItem('tenda_active_store', String(store.id))
  }

  const triggerSync = async () => {
  if (!activeStore) return
  await api.post(`/shopify/stores/${activeStore.id}/sync/`)
  await fetchStores()
  // Immediately update last_synced_at on the active store without waiting for full refetch
  setActiveStore(prev => prev ? {
    ...prev,
    last_synced_at: new Date().toISOString()
  } : prev)
}

  return (
    <Ctx.Provider value={{ stores, activeStore, loading, selectStore, fetchStores, triggerSync }}>
      {children}
    </Ctx.Provider>
  )
}

export const useStore = () => useContext(Ctx)
