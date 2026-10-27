import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
} from 'axios'
import { getDeviceId } from '../utils/device'
import { getSessionId, clearSession } from './session'

export const API_BASE = '/api/v1'
const PASSPORT_URL = import.meta.env.VITE_PASSPORT_URL as string | undefined
const REQUEST_TIMEOUT_MS = 30000

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: REQUEST_TIMEOUT_MS,
})

type SessionRequestConfig = InternalAxiosRequestConfig & { _sessionId?: string | null; _retry?: boolean }
const refreshRequests = new Map<string | null, Promise<void>>()

client.interceptors.request.use((config: SessionRequestConfig) => {
  const sessionId = getSessionId()
  if (config._sessionId === undefined) config._sessionId = sessionId
  if (config._sessionId !== sessionId) throw new axios.CanceledError('Session changed')
  const token = localStorage.getItem('access_token')
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  else config.headers.delete('Authorization')
  config.headers.set('X-Device-Id', getDeviceId())
  return config
})

async function refreshSession(sessionId: string | null, refresh: string) {
  const access = localStorage.getItem('access_token')
  const source = localStorage.getItem('auth_source') || 'local'
  const refreshUrl = source === 'passport' && PASSPORT_URL
    ? `${PASSPORT_URL}/api/v1/token/refresh/`
    : `${API_BASE}/auth/token/refresh/`
  try {
    const { data } = await axios.post(refreshUrl, { refresh }, {
      headers: { 'X-Device-Id': getDeviceId() },
      timeout: REQUEST_TIMEOUT_MS,
    })
    if (sessionId !== getSessionId()) throw new axios.CanceledError('Session changed')
    localStorage.setItem('access_token', data.access)
    if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
  } catch (error) {
    if (sessionId !== getSessionId()) throw new axios.CanceledError('Session changed')
    // 另一标签页可能已完成同会话续期，不能因旧刷新失败清掉它。
    const currentAccess = localStorage.getItem('access_token')
    if (currentAccess && currentAccess !== access) return
    clearSession()
    window.dispatchEvent(new Event('auth:logout'))
    throw error
  }
}

client.interceptors.response.use(
  (response: AxiosResponse) => {
    if ((response.config as SessionRequestConfig)._sessionId !== getSessionId()) {
      throw new axios.CanceledError('Session changed')
    }
    return response
  },
  async (error) => {
    const original = error.config as SessionRequestConfig | undefined
    if (original && original._sessionId !== getSessionId()) {
      throw new axios.CanceledError('Session changed')
    }
    if (error.response?.status !== 401 || !original || original._retry) throw error
    original._retry = true
    const access = localStorage.getItem('access_token')
    if (access && original.headers.get('Authorization') !== `Bearer ${access}`) {
      return client(original)
    }
    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) {
      window.dispatchEvent(new Event('auth:logout'))
      throw error
    }
    const sessionId = original._sessionId ?? null
    let pending = refreshRequests.get(sessionId)
    if (!pending) {
      pending = refreshSession(sessionId, refresh).finally(() => refreshRequests.delete(sessionId))
      refreshRequests.set(sessionId, pending)
    }
    await pending
    return client(original)
  },
)

export default client
