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
