/**
 * 展示层格式化工具
 * 对齐 prototype.html 里的 fmtNum / medalClass / rankBadge 等 helper，
 * 但补上了原型没考虑的真实数据情况（null、字符串型 Decimal、超长名称）。
 */

/** 原型 mock 里每所学校写死了一个 color，真实数据没有这个字段，用它按名称派生。 */
const ORG_PALETTE = [
  '#8b5cf6',
  '#06b6d4',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#3b82f6',
] as const

/**
 * 千分位。对齐原型 `n.toLocaleString('en-US')`。
 * 后端 DecimalField 序列化成字符串（如 "12847.50"），原型直接调 toLocaleString 会炸，
 * 这里统一先转数字；转不出来就原样回显，不吞掉异常数据。
 */
export function fmtNum(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return String(v)
  return n.toLocaleString('en-US')
}

/** 积分：保留 1 位小数再加千分位，避免 12847.5 和 12848 在同列上下跳。 */
export function fmtScore(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return String(v)
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
}

/** 整数计数（场数 / 人数）。null 显示破折号而不是 0，0 和"没数据"是两回事。 */
export function fmtCount(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return String(v)
}

export type MedalTier = 'gold' | 'silver' | 'bronze' | 'normal'

/** 名次 → 奖牌档位。对齐原型 rankBadge / medalClass。 */
export function medalTier(rank: number | null | undefined): MedalTier {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return 'normal'
}

/** 行左侧奖牌指示条的 class，非前三名返回空串。 */
export function medalRowClass(rank: number | null | undefined): string {
  const tier = medalTier(rank)
  return tier === 'normal' ? '' : `medal-row ${tier}`
}

/**
 * 按名称派生稳定配色（同一所学校每次刷新颜色一致）。
 * 用简单的 djb2 变体即可，不需要密码学强度。
 */
export function orgColor(name: string | null | undefined): string {
  const s = name || ''
  let h = 5381
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) | 0
  }
  return ORG_PALETTE[Math.abs(h) % ORG_PALETTE.length]
}

/**
 * 学校 logo 里的短标。
 * 优先用后端的 short_name（THU / ZJU），没有就从名称里挤一个出来：
 * 中文取前两字，英文取首字母缩写。
 */
export function orgShort(
  shortName: string | null | undefined,
  name: string | null | undefined,
): string {
  const s = (shortName || '').trim()
  if (s) return s.slice(0, 4).toUpperCase()
  const n = (name || '').trim()
  if (!n) return '?'
  if (/[\u4e00-\u9fa5]/.test(n)) return n.slice(0, 2)
  return n
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 4)
    .toUpperCase()
}

/** 头像里的首字。中文取首字，英文取首字母大写。 */
export function initial(name: string | null | undefined): string {
  const n = (name || '').trim()
  if (!n) return '?'
  return /[a-z]/.test(n[0]) ? n[0].toUpperCase() : n[0]
}

/** 日期时间：YYYY-MM-DD HH:mm，空值显示破折号。 */
export function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 平台代码 → 展示用标签（class + 文案）。对齐原型 platformTag。 */
export function platformTag(platform: string | null | undefined): {
  cls: string
  label: string
} {
  switch (platform) {
    case 'codeforces':
    case 'cf':
      return { cls: 'cf', label: 'CF' }
    case 'atcoder':
      return { cls: 'atcoder', label: 'AtCoder' }
    case 'nowcoder':
      return { cls: 'nowcoder', label: '牛客' }
    default:
      return { cls: 'atcoder', label: platform || '未知' }
  }
}

/**
 * 平台代码 → 英文名称（纯字符串）。
 * 用于分类标注等直接展示场景，避免模板里 `{{ platformTag(x) }}` 把 `{cls,label}`
 * 对象渲染成一串 JSON。
 */
export function platformName(platform: string | null | undefined): string {
  switch (platform) {
    case 'codeforces':
    case 'cf':
      return 'Codeforces'
    case 'atcoder':
      return 'AtCoder'
    case 'nowcoder':
      return 'NowCoder'
    default:
      return platform || '未知'
  }
}


// ==================== 竞赛日历展示口径 ====================
// 月历、三段看板与焦点卡共用，集中在这里避免两处派生逻辑漂移。

import type { Contest, ContestPlatform } from '../api/types'

export const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']

export type ContestStatus = 'ongoing' | 'upcoming' | 'finished'

export function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/** 赛事状态按时刻派生（不落库）。缺 end_time 一律按已结束处理。 */
export function contestStatus(c: Contest, at: number): ContestStatus {
  const s = c.start_time ? new Date(c.start_time).getTime() : null
  const e = c.end_time ? new Date(c.end_time).getTime() : null
  if (e !== null && e <= at) return 'finished'
  if (s !== null && s > at) return 'upcoming'
  if (s !== null && e !== null && s <= at && e > at) return 'ongoing'
  return 'finished'
}

export function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatDayMonth(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '时间待定'
  const d = new Date(iso)
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 周${WEEKDAYS[(d.getDay() + 6) % 7]} ${formatTime(iso)}`
}

export function formatDuration(min: number | null): string {
  if (!min || min <= 0) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h && m) return `${h}h ${pad2(m)}m`
  return h ? `${h}h` : `${m}m`
}

/** 跨了几个自然日（按本地时区） */
export function crossDays(c: Contest): number {
  if (!c.start_time || !c.end_time) return 0
  const a = new Date(c.start_time)
  const b = new Date(c.end_time)
  const da = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime()
  const db = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime()
  return Math.max(0, Math.round((db - da) / 86400000))
}

export function rangeLabel(c: Contest): string {
  if (!c.start_time) return '时间待定'
  if (!c.end_time) return `${formatDayMonth(c.start_time)} ${formatTime(c.start_time)} 起`
  const n = crossDays(c)
  const base = `${formatDayMonth(c.start_time)} ${formatTime(c.start_time)} – ${formatTime(c.end_time)}`
  return n > 0 ? `${base}（+${n}）` : base
}

export function platformTagClass(p: ContestPlatform): string {
  return p === 'codeforces' ? 'cf' : p === 'atcoder' ? 'atcoder' : 'nowcoder'
}

/** 倒计时四段固定（天/时/分/秒）：段数固定才不会每秒抖动布局 */
export function countdownParts(iso: string | null, at: number) {
  if (!iso) return []
  const ms = new Date(iso).getTime() - at
  if (ms <= 0) return []
  const s = Math.floor(ms / 1000)
  return [
    { k: '天', v: String(Math.floor(s / 86400)) },
    { k: '时', v: pad2(Math.floor(s / 3600) % 24) },
    { k: '分', v: pad2(Math.floor(s / 60) % 60) },
    { k: '秒', v: pad2(s % 60) },
  ]
}

/** 进行中赛事的已完成百分比（进度条宽度） */
export function progressPct(c: Contest | null, at: number): number {
  if (!c?.start_time || !c?.end_time) return 0
  const s = new Date(c.start_time).getTime()
  const e = new Date(c.end_time).getTime()
  if (e <= s) return 100
  return Math.min(100, Math.max(0, ((at - s) / (e - s)) * 100))
}

/** 相对时间一句话：3 天后开赛 / 2 小时 15 分后开赛 / 40 分后结束 */
export function relativeLabel(c: Contest, at: number): string {
  const st = contestStatus(c, at)
  const target = st === 'upcoming' ? c.start_time : c.end_time
  const ms = target ? new Date(target).getTime() - at : null
  if (ms === null || ms <= 0) return ''
  const min = Math.round(ms / 60000)
  if (min < 60) return st === 'upcoming' ? `${min} 分后开赛` : `${min} 分后结束`
  const h = Math.floor(min / 60)
  const tail = st === 'upcoming' ? '后开赛' : '后结束'
  if (h < 24) return `${h} 小时${min % 60 ? ` ${min % 60} 分` : ''}${tail}`
  return `${Math.round(h / 24)} 天${tail}`
}

/**
 * 行徽标。排期行（官方列出、尚未开赛）此前会显示成「非 Rated」，那是错的：
 * 它不是「不计分的比赛」，只是还没开始。
 */
export function rowBadge(c: Contest, at: number): { text: string; cls: string } {
  const st = contestStatus(c, at)
  if (st === 'upcoming') return { text: '未开赛', cls: 'badge-info' }
  if (st === 'ongoing') return { text: '进行中', cls: 'badge-success' }
  return c.is_rated
    ? { text: 'Rated', cls: 'badge-success' }
    : { text: '不计分', cls: 'badge-muted' }
}
