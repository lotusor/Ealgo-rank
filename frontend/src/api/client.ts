import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
} from 'axios'

export const API_BASE = '/api/v1'

// 统一认证中心地址（前端 .env 配置）；passport 登录的刷新请求打到这里
const PASSPORT_URL = import.meta.env.VITE_PASSPORT_URL as string | undefined

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

// 请求拦截：注入 Bearer Token
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// 响应拦截：401 时尝试用 refresh 续期一次
let isRefreshing = false
let pendingQueue: Array<() => void> = []

client.interceptors.response.use(
  (resp: AxiosResponse) => resp,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) {
        window.dispatchEvent(new Event('auth:logout'))
        return Promise.reject(error)
      }
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingQueue.push(() => resolve(client(original)))
        })
      }
      original._retry = true
      isRefreshing = true
      try {
        // passport 登录的令牌由 passport 签发，刷新必须打到 passport；本地账号走 algo_rank
        const source = localStorage.getItem('auth_source') || 'local'
        const refreshUrl =
          source === 'passport' && PASSPORT_URL
            ? `${PASSPORT_URL}/api/v1/token/refresh/`
            : `${API_BASE}/auth/token/refresh/`
        const { data } = await axios.post(refreshUrl, { refresh })
        localStorage.setItem('access_token', data.access)
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
        isRefreshing = false
        pendingQueue.forEach((fn) => fn())
        pendingQueue = []
        return client(original)
      } catch (e) {
        isRefreshing = false
        pendingQueue = []
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('auth_source')
        window.dispatchEvent(new Event('auth:logout'))
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

export default client
