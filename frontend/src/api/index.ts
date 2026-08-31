import client from './client'
import { createPkcePair } from '../utils/pkce'
import type {
  Paginated,
  PageQuery,
  UserMe,
  UserRoster,
  School,
  ScoreConfig,
  ContestDifficultyFactor,
  CrawlConfig,
  Application,
  CrawlJob,
  Participation,
  Contest,
  RankSnapshot,
  MyParticipation,
  UserPublicProfile,
  SchoolAdminApplicationCreate,
  UsernameAvailability,
  Announcement,
  AppNotification,
  PlatformAccount,
  SeasonInfo,
  PastSeason,
  UserBestRecord,
  ScoreRules,
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

// ---------- Lotus Passport OAuth（统一登录）----------
// 按官方接入契约（docs/integration/project1-ealgo-rank.md）：rank 自行调用护照
// API 的 /api/v1/oauth/{provider}/login/，取返回的 authorize_url 后跳转。
// 2026-08-27 起走「授权码 + PKCE」（OAuth 2.1 风格）：登录时带 code_challenge，
// 护照回调只回跳一次性 code（?code=...），由 AuthCallbackView 调
// exchangePassportCode() 换取 JWT——令牌不再经 URL fragment 下发（不进浏览器
// 历史/Referrer）。旧 fragment 模式仍兼容（护照侧未带 code_challenge 的旧链路）。
// 不要跳 account.eacm.cn/login —— 那是护照自己的 SPA，会把 token 发回它自己的
// 回调页，不会回跳 rank。
export type PassportProvider = 'github' | 'qq' | 'wechat'

export async function startPassportOAuth(provider: PassportProvider): Promise<void> {
  const pp =
    (import.meta.env.VITE_PASSPORT_URL as string | undefined) ||
    'https://passport.eacm.cn'
  const cb = `${window.location.origin}/auth/callback`
  const challenge = await createPkcePair()
  const url =
    `${pp}/api/v1/oauth/${provider}/login/?redirect_uri=${encodeURIComponent(cb)}` +
    `&code_challenge=${encodeURIComponent(challenge)}&code_challenge_method=S256`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  const data = (await resp.json().catch(() => ({}))) as {
    authorize_url?: string
    error?: { message?: string }
  }
  if (!resp.ok || !data.authorize_url) {
    throw new Error(data?.error?.message || '无法发起通行证登录，请稍后重试')
  }
  window.location.href = data.authorize_url
}

// 通用（provider 无关）莲花通行证登录：点击后跳转 passport 统一登录页，
// 登录方式（GitHub / QQ / 邮箱等）由通行证侧选择，完成后携授权码回本站。
export async function startPassportGenericLogin(): Promise<void> {
  const pp =
    (import.meta.env.VITE_PASSPORT_URL as string | undefined) ||
    'https://passport.eacm.cn'
  const cb = `${window.location.origin}/auth/callback`
  const challenge = await createPkcePair()
  const url =
    `${pp}/api/v1/oauth/login/?redirect_uri=${encodeURIComponent(cb)}` +
    `&code_challenge=${encodeURIComponent(challenge)}&code_challenge_method=S256`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  const data = (await resp.json().catch(() => ({}))) as {
    login_url?: string
    error?: { message?: string }
  }
  if (!resp.ok || !data.login_url) {
    throw new Error(data?.error?.message || '无法发起通行证登录，请稍后重试')
  }
  window.location.href = data.login_url
}

// 账号密码登录入口：同样先取一次性票据，再直达通行证的密码登录子页，
// 登录完成后仍走 /oauth/continue/ 携授权码回本站。
export async function startPassportPasswordLogin(): Promise<void> {
  const pp =
    (import.meta.env.VITE_PASSPORT_URL as string | undefined) ||
    'https://passport.eacm.cn'
  const cb = `${window.location.origin}/auth/callback`
  const challenge = await createPkcePair()
  const url =
    `${pp}/api/v1/oauth/login/?redirect_uri=${encodeURIComponent(cb)}` +
    `&code_challenge=${encodeURIComponent(challenge)}&code_challenge_method=S256`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  const data = (await resp.json().catch(() => ({}))) as {
    login_url?: string
    error?: { message?: string }
  }
  if (!resp.ok || !data.login_url) {
    throw new Error(data?.error?.message || '无法发起通行证登录，请稍后重试')
  }
  // login_url 形如 {web}/login?oticket=xxx → 直达密码登录子页
  window.location.href = data.login_url.replace('/login?', '/login/password?')
}

/** 授权码 + PKCE 换令牌：POST {passport}/api/v1/oauth/token/ {code, code_verifier}。 */
export async function exchangePassportCode(code: string, codeVerifier: string): Promise<{
  access: string
  refresh: string
  token_type: string
  passport_user_id: string
}> {
  const pp =
    (import.meta.env.VITE_PASSPORT_URL as string | undefined) ||
    'https://passport.eacm.cn'
  const resp = await fetch(`${pp}/api/v1/oauth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, code_verifier: codeVerifier }),
  })
  const data = (await resp.json().catch(() => ({}))) as {
    access?: string
    refresh?: string
    token_type?: string
    passport_user_id?: string
    error?: { message?: string }
  }
  if (!resp.ok || !data.access || !data.refresh) {
    throw new Error(data?.error?.message || '登录凭证交换失败，请重新登录')
  }
  return {
    access: data.access,
    refresh: data.refresh,
    token_type: data.token_type || 'Bearer',
    passport_user_id: data.passport_user_id || '',
  }
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

// ---------- 比赛难度系数（平台 × 系列 → 系数，超管管理） ----------
export async function listDifficultyFactors(params: PageQuery = {}) {
  const { data } = await client.get<Paginated<ContestDifficultyFactor>>(
    '/difficulty-factors/',
    { params },
  )
  return data
}

export async function updateDifficultyFactor(
  id: number,
  payload: Partial<ContestDifficultyFactor>,
) {
  const { data } = await client.patch<ContestDifficultyFactor>(
    `/difficulty-factors/${id}/`,
    payload,
  )
  return data
}

// ---------- Crawl config (自动爬取配置，单例) ----------
export async function getCrawlConfig(): Promise<CrawlConfig> {
  const { data } = await client.get<CrawlConfig>('/crawl-configs/')
  return data
}

export async function saveCrawlConfig(payload: Partial<CrawlConfig>): Promise<CrawlConfig> {
  // 后端 create() 为 upsert（忽略 pk，更新唯一配置），POST 即保存
  const { data } = await client.post<CrawlConfig>('/crawl-configs/', payload)
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

// ---------- 用户公开信息页（榜单点击跳转） ----------
export async function getUserPublicProfile(id: number): Promise<UserPublicProfile> {
  const { data } = await client.get<UserPublicProfile>(`/users/${id}/profile/`)
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

// ---------- 平台账号绑定 ----------
export async function listPlatformAccounts(): Promise<PlatformAccount[]> {
  // 后端 ModelViewSet 默认分页，返回 {count, results, ...}，这里取 results
  const { data } = await client.get<Paginated<PlatformAccount>>(
    '/platform-accounts/',
    { params: { page_size: 100 } },
  )
  return data.results
}

export async function bindPlatformAccount(payload: {
  platform: string
  handle: string
  display_name?: string
}): Promise<PlatformAccount> {
  const { data } = await client.post<PlatformAccount>('/platform-accounts/', payload)
  return data
}

export async function updatePlatformAccount(
  id: number,
  payload: { handle?: string; display_name?: string },
): Promise<PlatformAccount> {
  const { data } = await client.patch<PlatformAccount>(
    `/platform-accounts/${id}/`,
    payload,
  )
  return data
}

export async function unbindPlatformAccount(id: number): Promise<void> {
  await client.delete(`/platform-accounts/${id}/`)
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
  localStorage.setItem('auth_source', 'local') // 本地注册账号，刷新走 algo_rank
  return data
}

export async function updateMe(payload: {
  /** 仅 passport 首登占位用户名未认领时可写（一次性）；已认领后后端拒绝改名 */
  username?: string
  real_name?: string
  student_no?: string
  school_code?: string
  bio?: string
}): Promise<UserMe> {
  const { data } = await client.put<UserMe>('/me/', payload)
  return data
}

/** 更新头像（multipart 上传）。传 null 表示移除头像。 */
export async function updateAvatar(file: File | null): Promise<UserMe> {
  const fd = new FormData()
  if (file) fd.append('avatar', file)
  else fd.append('avatar', '')
  const { data } = await client.put<UserMe>('/me/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/**
 * 改密 / 设置本地密码（后端 /change-password/ 二合一）。
 * - 已设本地密码：需传 old_password（原密码）。
 * - passport 首登用户（无本地密码）：不传 old_password，直接设置首条本地密码。
 */
export async function setPassword(payload: {
  old_password?: string
  new_password1: string
  new_password2: string
}): Promise<{ detail: string }> {
  const { data } = await client.post<{ detail: string }>(
    '/change-password/',
    payload,
  )
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
  // 两种模式二选一：绑定已有学校，或申请系统里还没有的学校
  if (payload.school != null) {
    fd.append('school', String(payload.school))
  }
  if (payload.proposed_school_name) {
    fd.append('proposed_school_name', payload.proposed_school_name)
  }
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

// ---------- 赛季信息 ----------
export async function getSeason(): Promise<SeasonInfo> {
  const { data } = await client.get<SeasonInfo>('/season/')
  return data
}

export async function getPastSeasons(): Promise<PastSeason[]> {
  const { data } = await client.get<{ results: PastSeason[] }>('/season/past/')
  return data.results
}

// ---------- 积分规则公开页 / 用户最佳纪录 ----------
export async function getScoreRules(): Promise<ScoreRules> {
  const { data } = await client.get<ScoreRules>('/score-rules/')
  return data
}

export async function getMyBestRecord(): Promise<UserBestRecord> {
  const { data } = await client.get<UserBestRecord>('/me/best/')
  return data
}
