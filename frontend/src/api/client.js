import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
const api = axios.create({ baseURL, timeout: 30000 })

const token = localStorage.getItem('tenda_token')
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('tenda_token')
      delete api.defaults.headers.common['Authorization']
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

export const dashApi = {
  kpis:       (id, days=30) => api.get(`/dashboard/${id}/kpis/`,            { params:{days} }).then(r=>r.data),
  trend:      (id, days=30) => api.get(`/dashboard/${id}/revenue-trend/`,   { params:{days} }).then(r=>r.data),
  products:   (id, days=30, limit=10) => api.get(`/dashboard/${id}/top-products/`, { params:{days,limit} }).then(r=>r.data),
  categories: (id, days=30) => api.get(`/dashboard/${id}/category-revenue/`,{ params:{days} }).then(r=>r.data),
  locations:  (id, days=30) => api.get(`/dashboard/${id}/location-revenue/`,{ params:{days} }).then(r=>r.data),
  insights:   (id)          => api.get(`/dashboard/${id}/insights/`).then(r=>r.data),
}

export const inventoryApi = {
  overview: (id, status) => api.get(`/inventory/${id}/`, { params: status ? {status} : {} }).then(r=>r.data),
}

export const customerApi = {
  analytics: (id)       => api.get(`/customers/${id}/analytics/`).then(r=>r.data),
  list: (id, params={}) => api.get(`/customers/${id}/list/`, { params }).then(r=>r.data),
}

export const alertsApi = {
  list:    (id)          => api.get(`/alerts/${id}/`).then(r=>r.data),
  resolve: (id, alertId) => api.post(`/alerts/${id}/${alertId}/resolve/`).then(r=>r.data),
}
