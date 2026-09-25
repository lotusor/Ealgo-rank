/**
 * 平台元信息唯一来源。
 *
 * 为什么要单独立一个文件：`ContestPlatform` 联合类型、标签类名、显示名、绑定指引、
 * 首页卡片、后台可操作平台清单原先在 11 处各写一份，其中 5 个「类名/显示名」函数
 * 是三元链且 **else 分支返回另一个平台**（`format.ts` 里那句
 * `p === 'atcoder' ? 'atcoder' : 'nowcoder'`）。加第 4 个平台时，漏改的那几处不会
 * 报错，只会把洛谷渲染成牛客的绿色 —— 比缺样式更难发现。
 *
 * 这里用 `Record<PlatformKey, ...>` 兜底：少一个平台就编译不过；取不到的 key 一律
 * 返回「未知平台」而不是别人的颜色。
 *
 * 能力位（bindable / scoring / crawlable）必须与后端 `apps/common/platforms.py`
 * 的注册表一致：那侧是权威（接口 `/contests/meta/` 会随 `platforms[]` 下发同名
 * 字段），这里是展示层镜像。两边不一致时以接口为准，UI 文案不要写死平台数。
 */

export type PlatformKey = 'codeforces' | 'atcoder' | 'nowcoder' | 'luogu'

export interface PlatformMeta {
  key: PlatformKey
  /** 全称，用于列表与正文 */
  label: string
  /** 窄位（筛选 chip / 徽标 / 月历）用的短名 */
  chip: string
  /** 官方站点，用于首页卡片与外链文案 */
  site: string
  icon: string
  /** 首页平台卡的一句话介绍 */
  desc: string
  /** 绑定弹窗里的输入提示 */
  bindHint: string
  /** 去哪里找自己的 ID；不开放绑定的平台留空 */
  bindGuide: string
  /** 是否开放账号绑定（false = 不出现在绑定列表里） */
  bindable: boolean
  /** 是否参与积分（决定「平台系数」「成绩」类界面是否列它） */
  scoring: boolean
  /** 后台能否手动触发爬取（只做日历展示的平台没有榜单可爬） */
  crawlable: boolean
  /** 爬取窗口参数形状：count=最近 N 场，months_back=最近 N 个月。
   *  后台表单按它分支，别再写 `platform !== 'nowcoder'` 这种二元判断。 */
  crawlParam?: 'count' | 'months_back'
}

/** CSS 类名后缀就是 key 本身：`.platform-tag.codeforces`、`.cal-event.luogu`……
 *  不再另起一套缩写别名，避免「cf / codeforces」两套叫法在 5 个函数里各写一遍。 */
export function platformClass(key: string | null | undefined): string {
  return platformMeta(key)?.key ?? ''
}

export const PLATFORM_META: Record<PlatformKey, PlatformMeta> = {
  codeforces: {
    key: 'codeforces',
    label: 'Codeforces',
    chip: 'CF',
    site: 'codeforces.com',
    icon: 'https://codeforces.org/s/0/favicon-32x32.png',
    desc: '全球最活跃的算法竞赛平台，Rating 系统权威，高校选手主战场。',
    bindHint: '如 tourist',
    bindGuide: 'codeforces.com/profile 网址里的最后一段就是你的 handle',
    bindable: true,
    scoring: true,
    crawlable: true,
    crawlParam: 'count',
  },
  atcoder: {
    key: 'atcoder',
    label: 'AtCoder',
    chip: 'AtCoder',
    site: 'atcoder.jp',
    icon: 'https://atcoder.jp/favicon.ico',
    desc: '日本老牌竞赛平台，题目质量高，ABC / ARC 系列深受高校欢迎。',
    bindHint: '如 chokudai',
    bindGuide: 'atcoder.jp 右上角头像页上的 UserScreenName 即为账号 ID',
    bindable: true,
    scoring: true,
    crawlable: true,
    crawlParam: 'count',
  },
  nowcoder: {
    key: 'nowcoder',
    label: '牛客',
    chip: 'NC',
    site: 'ac.nowcoder.com',
    icon: 'https://www.nowcoder.com/favicon.ico',
    desc: '国内高校赛事核心阵地，多校训练赛、寒假集训营覆盖面广。',
    bindHint: '纯数字 uid',
    bindGuide: '竞赛站 ac.nowcoder.com 个人主页网址里 contest/profile/ 后面的数字，不是学号',
    bindable: true,
    scoring: true,
    crawlable: true,
    crawlParam: 'months_back',
  },
  luogu: {
    key: 'luogu',
    label: '洛谷',
    chip: 'LG',
    site: 'luogu.com.cn',
    icon: 'https://www.luogu.com.cn/favicon.ico',
    desc: '国内中学竞赛主阵地，月赛 / 基础赛 / 各校公开赛与重现赛节奏密集。',
    // 本期只做赛程展示：官方榜单页需要登录、用户页返回 403，取不到逐人名次，
    // 因此不计分、不开放绑定。能力位改起来只动这一处 + 后端注册表。
    bindHint: '',
    bindGuide: '',
    bindable: false,
    scoring: false,
    crawlable: false,
  },
}

/** 展示顺序的唯一来源（筛选项、卡片、下拉都按它排） */
export const PLATFORM_ORDER: PlatformKey[] = ['codeforces', 'atcoder', 'nowcoder', 'luogu']

export const ALL_PLATFORMS = PLATFORM_ORDER.map((k) => PLATFORM_META[k])

export const BINDABLE_PLATFORMS = ALL_PLATFORMS.filter((p) => p.bindable)
export const SCORING_PLATFORMS = ALL_PLATFORMS.filter((p) => p.scoring)
export const CRAWLABLE_PLATFORMS = ALL_PLATFORMS.filter((p) => p.crawlable)

/** 「三平台已绑定」这类文案不能再写死数字 */
export const BINDABLE_COUNT = BINDABLE_PLATFORMS.length

export function platformMeta(key: string | null | undefined): PlatformMeta | null {
  if (!key) return null
  return (PLATFORM_META as Record<string, PlatformMeta | undefined>)[key] ?? null
}

/** 显示名：未知平台原样吐出 key，便于排查数据而不是藏成别人的名字 */
export function platformLabel(key: string | null | undefined): string {
  return platformMeta(key)?.label ?? (key || '未知平台')
}

export function platformChip(key: string | null | undefined): string {
  return platformMeta(key)?.chip ?? (key || '未知平台')
}

export interface PlatformOption {
  label: string
  value: PlatformKey
}

/** 给 SegmentedControl / 下拉用的选项数组（不含「全部」，由各页自己前置） */
/** 可绑定平台的名字清单，用于注册/资料页的说明文案 */
export function bindableNames(separator = ' / '): string {
  return BINDABLE_PLATFORMS.map((p) => p.label).join(separator)
}

export function platformOptions(keys: PlatformMeta[] = ALL_PLATFORMS): PlatformOption[] {
  return keys.map((p) => ({ label: p.chip, value: p.key }))
}
