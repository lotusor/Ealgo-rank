// 后端返回的分页结构（StandardPagination）
export interface Paginated<T> {
  count: number
  page: number
  page_size: number
  total_pages: number
  results: T[]
}

// 通用选项
export interface PageQuery {
  page?: number
  page_size?: number
  [key: string]: any
}

// 用户 / 角色
export type UserRole = 'user' | 'school_admin' | 'super_admin'

// 平台账号（绑定到三大算法竞赛平台的账号 ID）
export interface PlatformAccount {
  id: number
  platform: 'codeforces' | 'atcoder' | 'nowcoder'
  platform_display: string
  handle: string
  display_name: string
  verified: boolean
  verified_at: string | null
  school: { id: number; name: string; short_name: string; code: string } | null
  created_at: string
  can_edit_handle: boolean
  handle_next_edit_at: string | null
}

export interface UserMe {
  id: number
  username: string
  email: string
  real_name: string
  student_no: string
  avatar: string | null
  bio: string
  role: UserRole
  role_display: string
  school: { id: number; name: string; short_name: string; code: string } | null
  school_bound_at: string | null
  platform_accounts: PlatformAccount[]
  is_super_admin: boolean
  is_school_admin: boolean
  /**
   * passport 首登时 username 用 passport_user_id(UUID) 占位，尚未由用户认领。
   * 为 true 时补全页的用户名框可编辑且必填；认领后后端锁定不可再改。
   */
  needs_username: boolean
  /**
   * 是否已设置本地密码。passport 首登用户为 false，可走「设置本地密码」流程。
   */
  has_usable_password: boolean
  date_joined: string
}

/** GET /username-available/ 的响应；available=false 时 reason 可直接展示给用户。 */
export interface UsernameAvailability {
  username: string
  available: boolean
  reason: string
}

export interface UserRoster {
  id: number
  username: string
  email: string
  real_name: string
  student_no: string
  role: UserRole
  role_display: string
  school: number | null
  school_name: string
  school_code: string
  school_bound_at: string | null
  platform_accounts_count: number
  is_super_admin: boolean
  is_school_admin: boolean
  date_joined: string
}

// 学校 / 评分配置
export interface School {
  id: number
  name: string
  short_name: string
  code: string
  logo: string | null
  description: string
  is_active: boolean
  member_count: number
}

export interface ScoreConfig {
  id: number
  cf_factor: string
  atcoder_factor: string
  nowcoder_factor: string
  default_contest_factor: string
  platform_weight: string
  contest_weight: string
  recent_contest_limit: number
  created_at: string
  updated_at: string
}

// 比赛难度系数（平台 × 系列 → 系数）
export interface ContestDifficultyFactor {
  id: number
  platform: string
  platform_display: string
  series: string
  factor: string
  created_at: string
  updated_at: string
}

// 自动爬取配置（CrawlConfig 单例）
export interface CrawlConfig {
  id: number
  enabled: boolean
  cf_count: number
  atcoder_count: number
  nowcoder_months_back: number
  auto_crawl_interval_days: number
  auto_crawl_hour: number
  created_at: string
  updated_at: string
}

// 管理员申请
export type ApplicationStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'cancelled'

export interface Application {
  id: number
  applicant: { id: number; username: string; real_name: string; role: string }
  school: { id: number; name: string; code: string } | null
  reason: string
  contact: string
  evidence: string | null
  status: ApplicationStatus
  status_display: string
  review_comment: string
  reviewer: number | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

// 爬虫任务
export type CrawlStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'partial'

export interface CrawlJob {
  id: number
  platform: string
  platform_display: string
  status: CrawlStatus
  status_display: string
  triggered_by: number | null
  triggered_by_name: string
  params: Record<string, any>
  celery_task_id: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  contest_count: number
  participation_count: number
  cheater_count: number
  error_message: string
  log: string
  created_at: string
}

// 参赛记录
export type ExcludeReason =
  | ''
  | 'cheater'
  | 'post_contest'
  | 'unbound'
  | 'manual'

export interface Participation {
  id: number
  contest: number
  contest_name: string
  contest_platform: string
  contest_platform_display: string
  contest_start_time: string
  contest_is_rated: boolean
  platform_account: number | null
  user_username: string
  user_real_name: string
  handle: string
  display_name: string
  rank: number | null
  total_score: number | null
  solved_count: number | null
  is_excluded: boolean
  exclude_reason: ExcludeReason
  exclude_reason_display: string
  extra?: Record<string, any>
  created_at: string
}

// 比赛（只读）
export type ContestPlatform = 'codeforces' | 'atcoder' | 'nowcoder'

export interface Contest {
  id: number
  platform: ContestPlatform
  platform_display: string
  external_id: string
  name: string
  url: string | null
  start_time: string | null
  end_time: string | null
  duration_minutes: number | null
  is_rated: boolean
  is_paid: boolean
  series: string | null
  difficulty_factor: string
  problem_count: number | null
  participant_count: number | null
  valid_participant_count: number | null
  cheater_count: number | null
  created_at: string
}

// 榜单快照（只读）
export type RankScope = 'school' | 'student'
export type RankPeriod = 'all' | string // "all" 或具体年份如 "2026"

export interface RankSnapshot {
  id: number
  scope: RankScope
  period: RankPeriod
  school: number | null
  school_name: string | null
  user: number | null
  user_name: string | null
  user_school_name: string | null
  user_avatar: string | null
  rank: number
  total_score: number
  contest_count: number
  member_count: number | null
  computed_at: string
}

// 赛季信息
export type SeasonStage = 'upcoming' | 'active' | 'settling' | 'ended'

export interface SeasonReward {
  title: string
  desc?: string
  icon?: string
}

export interface SeasonInfo {
  id: number
  year: number
  name: string
  start_at: string
  end_at: string
  settle_at: string | null
  stage: SeasonStage
  stage_display: string
  rewards: SeasonReward[]
  progress: { elapsed_days: number; total_days: number; pct: number }
  settle_countdown_seconds: number | null
  me: {
    rank: number | null
    total_score: number
    contest_count: number
  } | null
}

export interface PastSeason {
  id: number
  year: number
  name: string
  start_at: string
  end_at: string
  stage: SeasonStage
  stage_display: string
}

// 用户公开信息页（榜单点击跳转后展示）
export interface UserPublicProfile {
  id: number
  username: string
  real_name: string | null
  avatar: string | null
  bio: string
  school: number | null
  school_name: string
  role_display: string
  platform_ratings: { platform: string; handle: string; rating: number; delta: number | null }[]
  participations: MyParticipation[]
}

// 本人参赛记录（只读，仅本人可见）
export interface MyParticipation {
  id: number
  contest: number
  contest_name: string
  contest_platform: ContestPlatform
  contest_platform_display: string
  contest_start_time: string | null
  contest_is_rated: boolean
  contest_url: string | null
  platform: ContestPlatform
  platform_account: number | null
  user_username: string
  handle: string
  display_name: string
  rank: number | null
  solved_count: number | null
  penalty_ms: number | null
  rating_delta: number | null
  old_rating: number | null
  new_rating: number | null
  weighted_rating: number | null
  is_excluded: boolean
  exclude_reason: ExcludeReason
  exclude_reason_display: string
  extra?: Record<string, any>
  created_at: string
}

// 提交学校管理员申请
export interface SchoolAdminApplicationCreate {
  school?: number | null
  proposed_school_name?: string
  reason: string
  contact: string
  evidence?: File
}

// 系统公告（任务1）：用户端顶栏轮播展示 + 超管发布
export type AnnouncementLevel = 'info' | 'success' | 'warning' | 'danger'

export interface Announcement {
  id: number
  title: string
  content: string
  level: AnnouncementLevel
  level_display: string
  pinned: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

// 站内信（#1 超管发布 + 用户端收件箱）
export type NotificationType =
  | 'system'
  | 'application_received'
  | 'application_reviewed'
  | 'admin_message'

export interface AppNotification {
  id: number
  type: NotificationType
  type_display: string
  title: string
  message: string
  link: string
  is_read: boolean
  created_at: string
}
