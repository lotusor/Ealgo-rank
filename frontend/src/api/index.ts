import client from './client'
import type {
  Paginated,
  PageQuery,
  UserMe,
  UserRoster,
  School,
  ScoreConfig,
  Application,
  CrawlJob,
  Participation,
  Contest,
  RankSnapshot,
  MyParticipation,
  SchoolAdminApplicationCreate,
  UsernameAvailability,
  Announcement,
  AppNotification,
} from './types'

// ---------- Auth ----------
export async function login(username: string, password: string) {
  const { data } = await client.post('/auth/token/', { username, password })
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  localStorage.setItem('auth_source', 'local') // 本地密码登录（root/兜底），刷新走 algo_rank
  return data
}

export async function fetchMe(): Promise<UserMe> {
  const { data } = await client.get('/me/')
  return data
}

export async function logout() {
  // 尽力吊销 passport 侧 jti（离线验签不查黑名单，显式吊销更稳妥）
  const source = localStorage.getItem('auth_source')
  const token = localStorage.getItem('access_token')
  const pp = import.meta.env.VITE_PASSPORT_URL as string | undefined
  if (source === 'passport' && token && pp) {
    fetch(`${pp}/api/v1/logout/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {})
  }
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('auth_source')
}

// ---------- Schools ----------
export async function listSchools(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<School>>('/schools/', { params })
  return data
}

export async function getSchool(id: number) {
  const { data } = await client.get<School>(`/schools/${id}/`)
  return data
}

export async function updateSchool(id: number, payload: Partial<School>) {
  const { data } = await client.patch<School>(`/schools/${id}/`, payload)
  return data
}

export async function createSchool(payload: Partial<School>) {
  const { data } = await client.post<School>('/schools/', payload)
  return data
}

// ---------- Score config ----------
export async function listScoreConfigs(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<ScoreConfig>>('/score-configs/', {
    params,
  })
  return data
}

export async function getScoreConfig(id: number) {
  const { data } = await client.get<ScoreConfig>(`/score-configs/${id}/`)
  return data
}

export async function updateScoreConfig(
  id: number,
  payload: Partial<ScoreConfig>,
) {
  const { data } = await client.patch<ScoreConfig>(
    `/score-configs/${id}/`,
    payload,
  )
  return data
}

export async function createScoreConfig(payload: Partial<ScoreConfig>) {
  const { data } = await client.post<ScoreConfig>('/score-configs/', payload)
  return data
}

// ---------- Applications ----------
export async function listApplications(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<Application>>('/applications/', {
    params,
  })
  return data
}

export async function approveApplication(id: number, comment = '') {
  const { data } = await client.post<Application>(`/applications/${id}/approve/`, {
    review_comment: comment,
  })
  return data
}

export async function rejectApplication(id: number, comment = '') {
  const { data } = await client.post<Application>(`/applications/${id}/reject/`, {
    review_comment: comment,
  })
  return data
}

export async function cancelApplication(id: number) {
  const { data } = await client.post<Application>(`/applications/${id}/cancel/`)
  return data
}

// ---------- Crawl ----------
export async function listCrawlJobs(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<CrawlJob>>('/crawl-jobs/', {
    params,
  })
  return data
}

export async function triggerCrawl(payload: {
  platform: string
  count?: number
  months?: string[]
  months_back?: number
}) {
  const { data } = await client.post<CrawlJob>('/crawl-jobs/trigger/', payload)
  return data
}

export async function recomputeRanking() {
  const { data } = await client.post('/rankings/recompute/')
  return data
}

// ---------- Participations ----------
export async function listParticipations(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<Participation>>('/participations/', {
    params,
  })
  return data
}

export async function excludeParticipation(id: number) {
  const { data } = await client.post<Participation>(
    `/participations/${id}/exclude/`,
  )
  return data
}

export async function restoreParticipation(id: number) {
  const { data } = await client.post<Participation>(
    `/participations/${id}/restore/`,
  )
  return data
}

// ---------- Members (users) ----------
export async function listUsers(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<UserRoster>>('/users/', { params })
  return data
}

// ---------- Rankings (只读，用户端榜单) ----------
export async function listRankings(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<RankSnapshot>>('/rankings/', {
    params,
  })
  return data
}

// ---------- Contests (只读，用户端比赛列表) ----------
export async function listContests(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<Contest>>('/contests/', { params })
  return data
}

// ---------- My participations (仅本人可见) ----------
export async function listMyParticipations(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<MyParticipation>>(
    '/me/participations/',
    { params },
  )
  return data
}

// ---------- 注册 / 资料补全 ----------
export interface RegisterPayload {
  username: string
  password: string
  password2: string
  email?: string
  real_name?: string
  student_no?: string
  school_code?: string
}

export interface RegisterResult {
  user: UserMe
  access: string
  refresh: string
}

export async function register(payload: RegisterPayload): Promise<RegisterResult> {
  const { data } = await client.post<RegisterResult>('/register/', payload)
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  return data
}

export async function updateMe(payload: {
  /** 仅 passport 首登占位用户名未认领时可写（一次性）；已认领后后端拒绝改名 */
  username?: string
  real_name?: string
  student_no?: string
  school_code?: string
}): Promise<UserMe> {
  const { data } = await client.put<UserMe>('/me/', payload)
  return data
}

/**
 * 查询用户名是否可用（格式 / 保留字 / 占用，一次查全）。
 * 公开接口，注册页与 passport 首登认领页共用。后端挂了 anon 60/min 限流，
 * 所以调用方必须防抖，别逐字符发请求。
 */
export async function checkUsernameAvailable(
  username: string,
): Promise<UsernameAvailability> {
  const { data } = await client.get<UsernameAvailability>('/username-available/', {
    params: { username },
  })
  return data
}

// ---------- 管理员申请提交 ----------
export async function createApplication(payload: SchoolAdminApplicationCreate) {
  const fd = new FormData()
  fd.append('school', String(payload.school))
  fd.append('reason', payload.reason)
  fd.append('contact', payload.contact)
  if (payload.evidence) fd.append('evidence', payload.evidence)
  const { data } = await client.post('/applications/', fd)
  return data
}

// ---------- 系统公告 ----------
// 用户端公开列表（无需登录）：仅启用中的，后端按 pinned→updated_at 排序
export async function listAnnouncements(): Promise<Announcement[]> {
  const { data } = await client.get<Announcement[]>('/announcements/public/')
  return data
}

// 超管管理列表（含已停用），支持分页
export async function listAdminAnnouncements(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<Announcement>>('/announcements/', {
    params,
  })
  return data
}

export async function createAnnouncement(
  payload: Partial<Announcement>,
): Promise<Announcement> {
  const { data } = await client.post<Announcement>('/announcements/', payload)
  return data
}

export async function updateAnnouncement(
  id: number,
  payload: Partial<Announcement>,
): Promise<Announcement> {
  const { data } = await client.patch<Announcement>(
    `/announcements/${id}/`,
    payload,
  )
  return data
}

export async function deleteAnnouncement(id: number) {
  await client.delete(`/announcements/${id}/`)
}

// ---------- 站内信（#1） ----------
// 当前登录用户的收件箱（本人只读）
export async function fetchNotifications(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<AppNotification>>('/notifications/', {
    params,
  })
  return data
}

// 标记单条已读
export async function markNotificationRead(id: number) {
  const { data } = await client.post<AppNotification>(
    `/notifications/${id}/read/`,
  )
  return data
}

// 全部已读
export async function markAllNotificationsRead() {
  const { data } = await client.post('/notifications/read_all/')
  return data
}

// 超级管理员发布站内信（可指定 user_ids，省略则全站广播）
export async function publishNotification(payload: {
  title: string
  message?: string
  link?: string
  user_ids?: number[]
}) {
  const { data } = await client.post<{ count: number }>(
    '/notifications/publish/',
    payload,
  )
  return data
}
