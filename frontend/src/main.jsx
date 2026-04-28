import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Apply saved theme immediately to prevent flash
const saved = localStorage.getItem('tenda_theme') || 'dark'
document.documentElement.setAttribute('data-theme', saved)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
