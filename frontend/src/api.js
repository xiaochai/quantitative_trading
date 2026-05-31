export const API_BASE = (import.meta.env.VITE_API_BASE_PATH || '/api').replace(/\/+$/, '')

export function apiUrl(path) {
  const p = String(path || '')
  if (p.startsWith('/')) return `${API_BASE}${p}`
  return `${API_BASE}/${p}`
}

export function apiFetch(path, options) {
  return fetch(apiUrl(path), options)
}

