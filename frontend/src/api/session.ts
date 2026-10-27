export const SESSION_KEY = 'auth_session_id'

export function getSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY)
}

export function saveSession(access: string, refresh: string, source: string) {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
  localStorage.setItem('auth_source', source)
  localStorage.setItem(SESSION_KEY, crypto.randomUUID())
}

export function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('auth_source')
  localStorage.setItem(SESSION_KEY, crypto.randomUUID())
}
