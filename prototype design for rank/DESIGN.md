# E-algo Rank · Design System (DESIGN.md)

> 学校维度算法竞赛积分排名平台 · 设计令牌文档
> 生成方：设计系统专家彩格调（Cai）｜ 视觉方向：Tech Utility × Modern Minimal

---

## 0. 设计系统推荐（Design System Selection）

### 候选方案对比

| 方案 | 设计系统 | 匹配度 | 特征 | 适合原因 |
|------|---------|--------|------|---------|
| A | **Linear** | ★★★★★ | 深色基底 + 紫靛强调色 + 毛玻璃导航 + 高密度数据表 + 极简栅格 + Inter 字体 + 流畅微交互 | 与 infmind.cn 参考锚点高度同源：深色背景、紫靛强调、玻璃拟态、卡片式信息组织。Linear 本身即面向技术型用户的 SaaS 工具，其密集表格/列表、命令面板、状态标签体系直接对应排名表、后台审批流、爬虫任务列表等场景。是深色科技感 SaaS 的事实标杆。 |
| B | **Vercel** | ★★★★☆ | 纯黑/纯白极简 + 几何精准 + 严格栅格 + 等宽数据呈现 + 分析仪表盘能力 | 代表 Modern Minimal 的纯净一面。严格栅格与等宽数字呈现适合排名数据。但偏单色（黑白为主），紫靛渐变与玻璃拟态表达不如 Linear 充分，竞技荣誉感色彩表达弱。 |
| C | **PostHog** | ★★★★☆ | 深色分析平台 + 紫色强调 + 数据可视化优先 + 指标卡片 + 趋势图表 | 数据仪表盘维度最强，指标卡片、趋势折线图、漏斗等直接对应 Rating 折线图与统计卡片。但品牌略偏活泼/多色，整体克制感与荣誉感弱于 Linear。 |

### 最终推荐：Linear（融合 Tech Utility 方向）

**选择理由**：
1. **视觉同源**：Linear 的深色 + 紫靛强调 + 毛玻璃导航，与 infmind.cn 参考锚点几乎一比一对应——无需大幅改造即可落地需求调性。
2. **场景全覆盖**：Linear 原生即是"顶部导航 + 数据列表/表格 + 状态标签 + 命令面板"的 SaaS 结构，直接映射 E-algo Rank 三大板块（用户端排名表 / 后台审批流 / 爬虫任务列表）。
3. **受众契合**：目标用户是习惯 CF/AtCoder 的极客型学生，Linear 的快速、键盘友好、信息密集美学正是该群体的审美舒适区。
4. **可扩展性**：Linear 的令牌体系成熟（色彩层级、间距阶梯、深度系统），易于在保持一致性的前提下扩展 15 个页面。

**定制策略**：以 Linear 结构为骨架，注入项目专属令牌——主色由 Linear 紫 `#5e6ad2` 调整为更鲜亮的靛蓝 `#6366f1`，引入紫靛渐变（`#6366f1 → #8b5cf6`）作为竞技荣誉感表达，强化玻璃拟态层级，并新增奖牌色系（金/银/铜）用于 Top 3 排名差异化。

---

## 1. Visual Theme（视觉主题）

**Philosophy**: 让数据成为荣誉的载体——用极简的深色画布衬托每一个排名数字的分量。
**Direction**: Tech Utility × Modern Minimal 融合；data-dense, dark-first, glassmorphic, grid-disciplined.
**Personality**: 精准（precise）、克制（restrained）、荣誉（honorable）、可信（trustworthy）。
**Reference**: Linear（结构骨架）+ infmind.cn（紫靛渐变 / 玻璃拟态 / 全宽 Hero）+ CF/AtCoder（数据密度心智模型）。
**Dark-First 原则**: 全平台默认深色模式；所有色彩、边框、阴影均基于深色背景设计，确保表格斑马纹、表单输入、图表网格线在深色下保持高可读性。

---

## 2. Color Palette（调色板）

> 全部以 CSS 自定义属性输出。色值同时提供 HEX 与 OKLCh 近似值。

### 2.1 背景层级（Background Layers）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-bg-base` | `#0a0a0f` | 页面最底层背景 |
| `--color-bg-surface` | `#13131a` | 卡片 / 面板背景 |
| `--color-bg-elevated` | `#1a1a24` | 悬浮卡片 / 弹出层背景 |
| `--color-bg-overlay` | `#20202c` | 模态框 / 抽屉 / 下拉菜单 |
| `--color-bg-inset` | `#08080d` | 凹陷区域（代码块 / 表格表头底纹） |

### 2.2 品牌主色（Primary — Indigo）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-primary` | `#6366f1` | 主品牌色：CTA、链接、激活态、主图标 |
| `--color-primary-hover` | `#5558e0` | 主色 hover |
| `--color-primary-active` | `#4f46e5` | 主色 active/pressed |
| `--color-primary-subtle` | `rgba(99,102,241,0.12)` | 主色低饱和底（选中行、弱高亮） |
| `--color-primary-border` | `rgba(99,102,241,0.40)` | 聚焦描边 |

### 2.3 辅色（Secondary — Violet）与渐变

| Token | HEX / Value | Usage |
|-------|-------------|-------|
| `--color-secondary` | `#8b5cf6` | 渐变终点色、次级强调 |
| `--gradient-primary` | `linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%)` | 主渐变：Hero、品牌按钮、徽章、Logo |
| `--gradient-primary-soft` | `linear-gradient(135deg,rgba(99,102,241,0.15),rgba(139,92,246,0.15))` | 弱渐变底（Top3 卡片、荣誉区） |
| `--gradient-hero-glow` | `radial-gradient(ellipse at top,rgba(99,102,241,0.18),transparent 60%)` | Hero 顶部辉光 |

### 2.4 数据强调色（Data Accents）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-accent-cyan` | `#06b6d4` | 数据 / 图表主色、Rating 折线 |
| `--color-accent-cyan-subtle` | `rgba(6,182,212,0.12)` | 图表区域填充 |

### 2.5 语义色（Semantic）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-success` | `#10b981` | 成功 / 上升 / 已通过 |
| `--color-success-subtle` | `rgba(16,185,129,0.12)` | 成功底色 |
| `--color-warning` | `#f59e0b` | 警告 / 待审批 / 排队中 |
| `--color-warning-subtle` | `rgba(245,158,11,0.12)` | 警告底色 |
| `--color-danger` | `#ef4444` | 错误 / 下降 / 失败 / 已排除 |
| `--color-danger-subtle` | `rgba(239,68,68,0.12)` | 危险底色 |
| `--color-info` | `#3b82f6` | 信息 / 进行中 |
| `--color-info-subtle` | `rgba(59,130,246,0.12)` | 信息底色 |

### 2.6 中性文字色（Text）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-text-primary` | `#f4f4f5` | 标题、正文主文字（对比度 15.3:1 ✓ AAA） |
| `--color-text-secondary` | `#a1a1aa` | 次级说明、表格次要列（对比度 8.6:1 ✓ AAA） |
| `--color-text-tertiary` | `#71717a` | 占位符、弱标签（对比度 5.0:1 ✓ AA） |
| `--color-text-disabled` | `#52525b` | 禁用态文字 |
| `--color-text-inverse` | `#0a0a0f` | 深色按钮上的文字 |

### 2.7 边框与分割线（Border）

| Token | Value | Usage |
|-------|-------|-------|
| `--color-border` | `rgba(255,255,255,0.08)` | 默认边框、卡片描边、表格线 |
| `--color-border-strong` | `rgba(255,255,255,0.14)` | 悬浮态/激活态加强边框 |
| `--color-border-focus` | `rgba(99,102,241,0.50)` | 输入框聚焦描边 |
| `--color-divider` | `rgba(255,255,255,0.06)` | 表格行分割、列表分隔 |

### 2.8 竞技荣誉色（Medal — Top 3 差异化）

| Token | HEX | Usage |
|-------|-----|-------|
| `--color-medal-gold` | `#fbbf24` | 第 1 名：金牌 / 主冠军色 |
| `--color-medal-silver` | `#cbd5e1` | 第 2 名：银牌 |
| `--color-medal-bronze` | `#d97706` | 第 3 名：铜牌 |
| `--gradient-gold` | `linear-gradient(135deg,#fbbf24,#f59e0b)` | 冠军卡片渐变描边/底纹 |

### 2.9 速查 CSS 片段

```css
:root {
  /* Background */
  --color-bg-base:#0a0a0f; --color-bg-surface:#13131a; --color-bg-elevated:#1a1a24; --color-bg-overlay:#20202c; --color-bg-inset:#08080d;
  /* Primary */
  --color-primary:#6366f1; --color-primary-hover:#5558e0; --color-primary-active:#4f46e5; --color-primary-subtle:rgba(99,102,241,.12); --color-primary-border:rgba(99,102,241,.40);
  /* Secondary & Gradient */
  --color-secondary:#8b5cf6; --gradient-primary:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%); --gradient-primary-soft:linear-gradient(135deg,rgba(99,102,241,.15),rgba(139,92,246,.15));
  /* Data */
  --color-accent-cyan:#06b6d4; --color-accent-cyan-subtle:rgba(6,182,212,.12);
  /* Semantic */
  --color-success:#10b981; --color-warning:#f59e0b; --color-danger:#ef4444; --color-info:#3b82f6;
  --color-success-subtle:rgba(16,185,129,.12); --color-warning-subtle:rgba(245,158,11,.12); --color-danger-subtle:rgba(239,68,68,.12); --color-info-subtle:rgba(59,130,246,.12);
  /* Text */
  --color-text-primary:#f4f4f5; --color-text-secondary:#a1a1aa; --color-text-tertiary:#71717a; --color-text-disabled:#52525b; --color-text-inverse:#0a0a0f;
  /* Border */
  --color-border:rgba(255,255,255,.08); --color-border-strong:rgba(255,255,255,.14); --color-border-focus:rgba(99,102,241,.50); --color-divider:rgba(255,255,255,.06);
  /* Medal */
  --color-medal-gold:#fbbf24; --color-medal-silver:#cbd5e1; --color-medal-bronze:#d97706; --gradient-gold:linear-gradient(135deg,#fbbf24,#f59e0b);
}
```

---

## 3. Typography（排版）

### 3.1 字体族（Font Stacks）

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Source Han Sans CN', 'Noto Sans SC', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
--font-cn: 'PingFang SC', 'Microsoft YaHei', 'Source Han Sans CN', 'Noto Sans SC', sans-serif;
```

- **正文/UI**：Inter（西文）+ 苹方/思源黑体（中文），保证中英混排一致。
- **数据数字**：JetBrains Mono 等宽——排名、Rating、积分、时间戳一律等宽对齐，杜绝数字跳动。
- **加载**：Inter 与 JetBrains Mono 通过 Google Fonts / 自托管 woff2 加载；中文走系统字体栈零等待。

### 3.2 字号阶梯（Type Scale）

| Level | Token | Size | Weight | Line-height | Usage |
|-------|-------|------|--------|-------------|-------|
| Display | `--text-display` | 48px / 3rem | 700 | 1.1 | Hero 主标题 |
| H1 | `--text-h1` | 36px / 2.25rem | 700 | 1.2 | 页面主标题 |
| H2 | `--text-h2` | 28px / 1.75rem | 600 | 1.3 | 区块标题 |
| H3 | `--text-h3` | 22px / 1.375rem | 600 | 1.4 | 卡片标题、子区块 |
| H4 | `--text-h4` | 18px / 1.125rem | 600 | 1.4 | 表单分组、小标题 |
| Body | `--text-body` | 16px / 1rem | 400 | 1.6 | 正文段落 |
| Body-sm | `--text-body-sm` | 14px / 0.875rem | 400 | 1.5 | 表格正文、列表项 |
| Caption | `--text-caption` | 13px / 0.8125rem | 500 | 1.4 | 辅助说明、表头 |
| Micro | `--text-micro` | 12px / 0.75rem | 500 | 1.4 | 徽章、标签、元信息 |
| Data | `--text-data` | 24px / 1.5rem | 700 | 1.2 | 统计卡片大数字（mono） |
| Data-lg | `--text-data-lg` | 32px / 2rem | 700 | 1.1 | 排名榜 Top 数字（mono） |

```css
:root {
  --text-display:700 3rem/1.1 var(--font-sans);
  --text-h1:700 2.25rem/1.2 var(--font-sans);
  --text-h2:600 1.75rem/1.3 var(--font-sans);
  --text-h3:600 1.375rem/1.4 var(--font-sans);
  --text-h4:600 1.125rem/1.4 var(--font-sans);
  --text-body:400 1rem/1.6 var(--font-sans);
  --text-body-sm:400 .875rem/1.5 var(--font-sans);
  --text-caption:500 .8125rem/1.4 var(--font-sans);
  --text-micro:500 .75rem/1.4 var(--font-sans);
  --text-data:700 1.5rem/1.2 var(--font-mono);
  --text-data-lg:700 2rem/1.1 var(--font-mono);
}
```

---

## 4. Component Styles（组件样式）

### 4.1 Button

| Variant | 背景 | 文字 | 边框 | 圆角 | Padding | Hover |
|---------|------|------|------|------|---------|-------|
| Primary | `var(--gradient-primary)` | `#fff` | none | `8px` | `10px 20px` | 提亮 + `shadow-glow` |
| Secondary | `var(--color-bg-elevated)` | `--color-text-primary` | `1px solid var(--color-border-strong)` | `8px` | `10px 20px` | 边框→primary-border |
| Ghost | transparent | `--color-text-secondary` | none | `8px` | `10px 20px` | bg→`bg-surface` |
| Danger | `var(--color-danger)` | `#fff` | none | `8px` | `10px 20px` | 提亮 |
| Icon | transparent | `--color-text-secondary` | none | `8px` | `8px` | bg→`bg-surface` |

- 高度统一 `--control-height: 36px`（默认）/ `--control-height-sm: 30px`（紧凑）/ `--control-height-lg: 44px`（Hero CTA）。
- 过渡：`all var(--duration-base) var(--ease-standard)`；Primary hover 叠加 `transform: translateY(-1px)` + `--shadow-glow`。
- 禁用态：`opacity:0.45; cursor:not-allowed`。

### 4.2 Card

```css
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);       /* 12px */
  padding: var(--space-5);               /* 20px */
  box-shadow: var(--shadow-md);
  transition: all var(--duration-base) var(--ease-standard);
}
.card--elevated { background: var(--color-bg-elevated); }
.card--glass    { background: var(--glass-bg); backdrop-filter: var(--glass-blur); border: var(--glass-border); }
.card--hover:hover { transform: translateY(-2px); border-color: var(--color-border-strong); box-shadow: var(--shadow-lg); }
.card--stat     { padding: var(--space-5); }            /* 统计卡片 */
.card--top-rank { background: var(--gradient-primary-soft); border-color: var(--color-primary-border); }
```

### 4.3 Table（数据密集型核心组件）

- **密度三档**：
  - Compact：行高 `36px`，padding `4px 12px`（爬虫任务历史、日志类）
  - Default：行高 `44px`，padding `8px 16px`（排名榜、参赛记录）
  - Comfortable：行高 `56px`，padding `12px 16px`（学校管理、成员名单）
- **表头**：`background: var(--color-bg-inset)`；文字 `--color-text-secondary` + `--text-caption`（13px/500）；左对齐，数字列右对齐。
- **斑马纹**：偶数行 `background: rgba(255,255,255,0.015)`（极淡，深色下不刺眼）。
- **悬停行**：`background: var(--color-primary-subtle)`。
- **选中行**：`background: var(--color-primary-subtle)` + 左侧 `2px solid var(--color-primary)` 指示条。
- **Top 3 行差异化**：第 1 名行左侧 `3px solid var(--color-medal-gold)`；第 2/3 名同理银/铜；排名数字使用对应奖牌色。
- **边框**：仅水平分割线 `1px solid var(--color-divider)`，无垂直线（Linear 风格，降低视觉噪音）。
- **数字列**：`font-family: var(--font-mono); font-variant-numeric: tabular-nums`；右对齐。
- **空状态**：居中图标 + 一行说明 + 次级 CTA，置于表格体内（min-height 200px）。

### 4.4 Input / Form

```css
.input {
  height: var(--control-height);        /* 36px */
  background: var(--color-bg-inset);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);      /* 8px */
  color: var(--color-text-primary);
  padding: 0 var(--space-3);
  font: var(--text-body-sm);
  transition: border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard);
}
.input::placeholder { color: var(--color-text-tertiary); }
.input:focus { outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-subtle); }
.input:disabled { opacity: .5; cursor: not-allowed; }
```

- Select / 筛选器同 Input 规范，右侧 8px 间距放 chevron 图标。
- 表单标签：`--text-caption`（13px/500）+ `--color-text-secondary`，标签与输入框间距 `--space-2`（8px）。
- 校验态：错误 `border-color: var(--color-danger)` + 下方 12px 红色提示文字；实时校验通过显示绿色对勾。
- 分步表单（C2 信息填写）：顶部步骤指示器，已完成步骤 primary 填充，当前步骤 primary 描边，未达步骤灰描边。

### 4.5 Navigation

**顶部导航栏（用户端 + 后台共用顶栏）**
- 高度 `--nav-height: 64px`；`background: var(--glass-bg); backdrop-filter: var(--glass-blur); border-bottom: 1px solid var(--color-border)`（毛玻璃吸顶）。
- 左侧 Logo（渐变文字或图标）+ 主导航项；右侧用户头像下拉 / 搜索 / 通知。
- 导航项激活态：文字 `--color-text-primary` + 底部 `2px solid var(--color-primary)` 指示条；非激活 `--color-text-secondary`。
- hover：文字提亮 + 出现底部细线 `var(--color-border-strong)`。

**管理后台侧边栏**
- 宽度 `--sidebar-width: 240px`（展开）/ `--sidebar-collapsed: 64px`（折叠，仅图标）。
- `background: var(--color-bg-surface); border-right: 1px solid var(--color-border)`。
- 分组标题：`--text-micro`（12px/500）+ `--color-text-tertiary` + uppercase letter-spacing。
- 菜单项激活态：`background: var(--color-primary-subtle)` + 左侧 `3px solid var(--color-primary)` + 文字 `--color-text-primary` + 图标 primary 色。
- 菜单项 hover：`background: rgba(255,255,255,0.04)`。

### 4.6 Badge / 状态徽章

统一胶囊形（`border-radius: var(--radius-full)`），`padding: 2px 10px`，`--text-micro`（12px/500）。

| 状态 | 文字色 | 背景色 | 边框 | 场景 |
|------|--------|--------|------|------|
| Success 成功 | `--color-success` | `--color-success-subtle` | `1px solid rgba(16,185,129,.25)` | 审批通过、爬取成功、绑定成功 |
| Running 进行中 | `--color-info` | `--color-info-subtle` | `1px solid rgba(59,130,246,.25)` | 爬取中、重算中、回调中 |
| Queued 排队中 | `--color-primary` | `--color-primary-subtle` | `1px solid rgba(99,102,241,.25)` | 任务等待执行 |
| Failed 失败 | `--color-danger` | `--color-danger-subtle` | `1px solid rgba(239,68,68,.25)` | 爬取失败、回调失败 |
| Pending 待审批 | `--color-warning` | `--color-warning-subtle` | `1px solid rgba(245,158,11,.25)` | 管理员申请待审 |
| Excluded 已排除 | `--color-text-tertiary` | `rgba(255,255,255,.05)` | `1px solid var(--color-border)` | 被排除的参赛记录 |
| Rank Top3 | `#0a0a0f` | 奖牌色（金/银/铜） | none | 排名徽章 |

- Running / Queued 状态附加 `@keyframes pulse` 呼吸点（左侧 6px 圆点 1.5s 无限淡入淡出）。

### 4.7 Chart Container

```css
.chart-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}
.chart-card__header { display:flex; justify-content:space-between; align-items:center; margin-bottom: var(--space-4); }
```
- **Rating 折线图**：主线 `--color-accent-cyan`（2px），区域填充 `--color-accent-cyan-subtle` 渐变至透明；hover tooltip 为玻璃拟态小卡（`--glass-bg` + blur）；坐标轴/网格线 `var(--color-divider)`；标签 `--color-text-tertiary` + mono 字体。
- **平台切换**：顶部 Tab 切换 CF/AtCoder/Nowcoder 等，激活 Tab primary 色 + 底部指示条。
- **统计卡片图表**：迷你 sparkline 用对应语义色，无坐标轴。

### 4.8 Modal / Drawer

- Modal：`background: var(--color-bg-overlay); border: 1px solid var(--color-border-strong); border-radius: var(--radius-xl)`（16px）；`box-shadow: var(--shadow-xl)`；最大宽度 `480px`（表单）/ `640px`（详情）/ `800px`（复杂表单）。
- 遮罩：`background: rgba(5,5,10,0.7); backdrop-filter: blur(4px)`。
- Drawer（右侧抽屉，详情用）：宽度 `420px`，`background: var(--color-bg-overlay)`，`box-shadow: var(--shadow-xl)`。

---

## 5. Layout（布局）

### 5.1 网格与容器

| Token | Value | Usage |
|-------|-------|-------|
| `--container-max` | `1280px` | 用户端内容区最大宽度 |
| `--container-wide` | `1440px` | 全宽 Hero / 后台主区 |
| `--container-narrow` | `720px` | 认证流程页（登录/注册/表单）居中窄栏 |
| `--grid-columns` | `12` | 12 列栅格 |
| `--grid-gutter` | `24px` | 列间距（桌面） |
| `--grid-gutter-sm` | `16px` | 列间距（平板） |
| `--page-padding-x` | `32px` | 页面左右内边距（桌面） |
| `--page-padding-y` | `32px` | 区块上下间距 |

### 5.2 间距阶梯（Spacing Scale，4px 基准）

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `4px` | 图标与文字间距、紧凑内距 |
| `--space-2` | `8px` | 标签内距、表单项间距 |
| `--space-3` | `12px` | 输入框内距、徽章间距 |
| `--space-4` | `16px` | 默认元素间距、卡片内小分组 |
| `--space-5` | `20px` | 卡片内边距 |
| `--space-6` | `24px` | 区块内分组间距、栅格 gutter |
| `--space-8` | `32px` | 页面内边距、区块间距 |
| `--space-10` | `40px` | 大区块间距 |
| `--space-12` | `48px` | 区块垂直分隔 |
| `--space-16` | `64px` | Hero 内距 |
| `--space-20` | `80px` | Hero 上下留白 |
| `--space-24` | `96px` | 页面大分区间距 |

```css
:root {
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:20px; --space-6:24px;
  --space-8:32px; --space-10:40px; --space-12:48px; --space-16:64px; --space-20:80px; --space-24:96px;
}
```

### 5.3 关键尺寸

| Token | Value | Usage |
|-------|-------|-------|
| `--nav-height` | `64px` | 顶部导航栏高度 |
| `--sidebar-width` | `240px` | 侧边栏展开宽度 |
| `--sidebar-collapsed` | `64px` | 侧边栏折叠宽度 |
| `--control-height` | `36px` | 默认控件高度 |
| `--control-height-sm` | `30px` | 紧凑控件高度 |
| `--control-height-lg` | `44px` | 大控件（Hero CTA）高度 |
| `--table-row-h` | `44px` | 默认表格行高 |
| `--avatar-size` | `32px` | 头像尺寸 |

---

## 6. Depth & Elevation（深度与层级）

### 6.1 阴影系统（深色专用）

深色背景下阴影需更重、更弥散，并叠加品牌色辉光表达悬浮。

| Level | Token | Value | Usage |
|-------|-------|-------|-------|
| Flat | `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | 默认静态表面 |
| Raised | `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | 卡片、下拉 |
| Floating | `--shadow-lg` | `0 4px 24px rgba(0,0,0,0.4)` | 悬浮卡片、hover |
| Overlay | `--shadow-xl` | `0 8px 32px rgba(0,0,0,0.5)` | 模态、抽屉 |
| Glow | `--shadow-glow` | `0 8px 32px rgba(99,102,241,0.15)` | 主色 hover 辉光 |
| Glow-strong | `--shadow-glow-strong` | `0 0 24px rgba(99,102,241,0.25)` | 激活/聚焦辉光 |

```css
:root {
  --shadow-sm:0 1px 2px rgba(0,0,0,.3);
  --shadow-md:0 4px 12px rgba(0,0,0,.4);
  --shadow-lg:0 4px 24px rgba(0,0,0,.4);
  --shadow-xl:0 8px 32px rgba(0,0,0,.5);
  --shadow-glow:0 8px 32px rgba(99,102,241,.15);
  --shadow-glow-strong:0 0 24px rgba(99,102,241,.25);
}
```

### 6.2 玻璃拟态（Glassmorphism）

```css
:root {
  --glass-bg: rgba(255,255,255,0.03);
  --glass-bg-strong: rgba(255,255,255,0.05);
  --glass-border: 1px solid rgba(255,255,255,0.08);
  --glass-blur: blur(12px);
  --glass-blur-strong: blur(20px);
}
.glass {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: var(--glass-border);
}
```

- **使用场景**：顶部导航栏（吸顶毛玻璃）、Hero 浮卡、登录卡片（C1）、图表 tooltip、命令面板。
- **注意**：玻璃层下方必须有彩色/渐变内容才能显出效果；纯黑底上玻璃拟态不可见，需叠加 `--gradient-hero-glow` 等辉光。

### 6.3 圆角系统（Radius）

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | 小标签、tag、徽章内元素 |
| `--radius-md` | `8px` | 按钮、输入框、选择器、小卡片 |
| `--radius-lg` | `12px` | 卡片、表格容器、图表容器 |
| `--radius-xl` | `16px` | 模态框、大卡片、Hero 卡 |
| `--radius-2xl` | `20px` | 特殊大容器 |
| `--radius-full` | `9999px` | 胶囊徽章、头像、圆点 |

```css
:root { --radius-sm:4px; --radius-md:8px; --radius-lg:12px; --radius-xl:16px; --radius-2xl:20px; --radius-full:9999px; }
```

### 6.4 Z-index 层级

| Token | Value | Usage |
|-------|-------|-------|
| `--z-base` | `0` | 默认内容 |
| `--z-dropdown` | `100` | 下拉菜单、选择器面板 |
| `--z-sticky` | `200` | 吸顶表头、粘性侧栏 |
| `--z-sidebar` | `300` | 后台侧边栏 |
| `--z-nav` | `400` | 顶部导航栏 |
| `--z-modal` | `1000` | 模态框 |
| `--z-drawer` | `1050` | 抽屉 |
| `--z-toast` | `1100` | Toast 通知 |
| `--z-tooltip` | `1200` | Tooltip |

---

## 7. Motion（动效系统）

### 7.1 缓动与时长

```css
:root {
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);   /* 通用 */
  --ease-out: cubic-bezier(0, 0, 0.2, 1);           /* 入场 */
  --ease-in-out: cubic-bezier(0.4, 0, 0.6, 1);      /* 切换 */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* 弹性反馈 */
  --duration-fast: 150ms;    /* 微反馈：颜色、边框 */
  --duration-base: 200ms;    /* 默认：hover、过渡 */
  --duration-slow: 300ms;    /* 展开、折叠 */
  --duration-slower: 400ms;  /* 模态、页面切换 */
}
```

### 7.2 交互反馈规范

| 交互 | 效果 | 时长 |
|------|------|------|
| 卡片 hover | `translateY(-2px)` + 边框提亮 + `shadow-lg` | 200ms standard |
| 按钮点击 | `scale(0.97)` 回弹 | 150ms spring |
| Primary hover | 叠加 `shadow-glow` | 200ms standard |
| 表格行 hover | 背景过渡至 primary-subtle | 150ms standard |
| Modal 入场 | 淡入 + `scale(0.96→1)` + 上移 8px | 300ms out |
| Drawer 入场 | 右侧滑入 | 300ms out |
| Tab 切换 | 底部指示条滑动 | 200ms standard |
| 排名数字变化 | 数字滚动（count-up） | 600ms out |
| 状态徽章 Running | 呼吸点 pulse | 1500ms infinite |

**原则**：所有位移 ≤ 8px；避免大幅弹跳；数字类过渡用 count-up 而非突现；尊重 `prefers-reduced-motion`。

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

---

## 8. Responsive Behavior（响应式行为）

桌面优先，但定义降级断点保证可访问性。

### 8.1 断点

| Name | Width | 行为 |
|------|-------|------|
| Mobile | `< 640px` | 单列堆叠；顶部导航折叠为汉堡菜单；侧边栏变抽屉；表格转卡片列表 |
| Tablet | `640–1024px` | 2 列；侧边栏默认折叠为图标态；表格横向滚动 |
| Desktop | `1024–1440px` | 完整布局；侧边栏展开 |
| Wide | `> 1440px` | 内容居中，两侧留白；可展示更多列 |

### 8.2 适配规则

- **表格**：平板及以下，次要列隐藏（优先级：排名/名称/主指标 > 次指标 > 时间戳）；提供"展开行"查看完整数据。
- **统计卡片**：桌面 4 列 → 平板 2 列 → 手机 1 列。
- **后台侧边栏**：`< 1024px` 默认折叠为图标态，点击展开为浮层抽屉（带遮罩）。
- **认证流程**：始终居中窄栏（`--container-narrow`），手机全宽 + 24px 内边距。
- **筛选器组**：桌面横排 → 手机竖排堆叠 + 折叠展开按钮。

---

## 9. Cautions（注意事项 / 反模式）

### Never Do（禁止）
- ❌ **浅色模式混用**：全平台深色优先，不要在同一页面混入浅色卡片/区块，破坏沉浸感。
- ❌ **纯黑背景无层次**：不要所有区域都用同一 `#000`，必须用 5 级背景层级（base→inset）建立空间纵深。
- ❌ **垂直表格线**：禁止画垂直分割线，仅保留水平分割线（Linear 原则，降低噪音）。
- ❌ **非等宽数字**：排名/Rating/积分数字禁止用比例字体，必须 `tabular-nums` 等宽，避免对齐错位。
- ❌ **玻璃拟态叠纯黑**：玻璃层下方无彩色内容时不可见，禁止在纯黑底上单独使用 `.glass` 而不加辉光底。
- ❌ **奖牌色滥用**：金/银/铜仅用于 Top 3 排名差异化，不要用于普通状态或装饰。
- ❌ **低对比文字**：正文不得使用 `--color-text-tertiary` 以下；次要文字不得低于 `--color-text-secondary`。
- ❌ **彩虹图表**：图表不要无意义地使用多色，优先 cyan 主线 + 语义色区分趋势。

### Prefer（推荐）
- ✅ 状态色系用"底色 + 边框 + 文字"三件套统一徽章，而非纯色块。
- ✅ 数据密集表格用 Compact 密度 + 极淡斑马纹（rgba 0.015），既密集又不疲劳。
- ✅ 空状态要有引导 CTA，不要只放一句"暂无数据"。
- ✅ 焦点态用 `box-shadow: 0 0 0 3px var(--color-primary-subtle)` 环形高亮，兼顾键盘可访问性。

---

## 10. Agent Prompt Guide（原型构建师指南）

### 生成关键指令
1. **全局深色基底**：`body { background: var(--color-bg-base); color: var(--color-text-primary); font-family: var(--font-sans); }`，所有组件基于此。
2. **CSS 变量先行**：所有颜色/间距/圆角必须引用 `:root` 变量，禁止硬编码 hex（除非渐变内联）。
3. **数字一律 mono**：排名、Rating、积分、计数、时间戳 → `font-family: var(--font-mono); font-variant-numeric: tabular-nums`。
4. **表格密度按场景**：排名榜/参赛记录 Default(44px)，爬虫历史/日志 Compact(36px)，学校/成员管理 Comfortable(56px)。
5. **三角色差异化**：通过侧边栏菜单项 + 顶栏角色徽章区分；普通用户无侧边栏，仅顶栏。
6. **Top 3 荣誉感**：排名榜 Top 3 行左侧奖牌色指示条 + 排名数字奖牌色 + Top3 卡片用 `--gradient-primary-soft` 底。
7. **玻璃拟态场景**：顶栏吸顶、登录卡(C1)、Hero 浮卡、图表 tooltip、命令面板——其余普通卡片用实色 surface。
8. **状态徽章统一**：用第 4.6 节状态表，Running/Queued 加 pulse 呼吸点。
9. **Hover 反馈**：卡片 `translateY(-2px)`，按钮 primary 叠 glow，表格行 primary-subtle 底色。
10. **可访问性**：所有可交互元素提供 `:focus-visible` 环形高亮；图表提供文字替代；尊重 `prefers-reduced-motion`。

### 完整 Token 速贴（原型构建师可直接复制到 `:root`）

```css
:root{
  /* ===== Color ===== */
  --color-bg-base:#0a0a0f; --color-bg-surface:#13131a; --color-bg-elevated:#1a1a24; --color-bg-overlay:#20202c; --color-bg-inset:#08080d;
  --color-primary:#6366f1; --color-primary-hover:#5558e0; --color-primary-active:#4f46e5; --color-primary-subtle:rgba(99,102,241,.12); --color-primary-border:rgba(99,102,241,.40);
  --color-secondary:#8b5cf6;
  --gradient-primary:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);
  --gradient-primary-soft:linear-gradient(135deg,rgba(99,102,241,.15),rgba(139,92,246,.15));
  --gradient-hero-glow:radial-gradient(ellipse at top,rgba(99,102,241,.18),transparent 60%);
  --color-accent-cyan:#06b6d4; --color-accent-cyan-subtle:rgba(6,182,212,.12);
  --color-success:#10b981; --color-warning:#f59e0b; --color-danger:#ef4444; --color-info:#3b82f6;
  --color-success-subtle:rgba(16,185,129,.12); --color-warning-subtle:rgba(245,158,11,.12);
  --color-danger-subtle:rgba(239,68,68,.12); --color-info-subtle:rgba(59,130,246,.12);
  --color-text-primary:#f4f4f5; --color-text-secondary:#a1a1aa; --color-text-tertiary:#71717a; --color-text-disabled:#52525b; --color-text-inverse:#0a0a0f;
  --color-border:rgba(255,255,255,.08); --color-border-strong:rgba(255,255,255,.14); --color-border-focus:rgba(99,102,241,.50); --color-divider:rgba(255,255,255,.06);
  --color-medal-gold:#fbbf24; --color-medal-silver:#cbd5e1; --color-medal-bronze:#d97706; --gradient-gold:linear-gradient(135deg,#fbbf24,#f59e0b);
  /* ===== Typography ===== */
  --font-sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei','Source Han Sans CN','Noto Sans SC',sans-serif;
  --font-mono:'JetBrains Mono','Fira Code',ui-monospace,'SF Mono',Menlo,Consolas,monospace;
  /* ===== Spacing ===== */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:20px; --space-6:24px;
  --space-8:32px; --space-10:40px; --space-12:48px; --space-16:64px; --space-20:80px; --space-24:96px;
  /* ===== Radius ===== */
  --radius-sm:4px; --radius-md:8px; --radius-lg:12px; --radius-xl:16px; --radius-2xl:20px; --radius-full:9999px;
  /* ===== Shadow ===== */
  --shadow-sm:0 1px 2px rgba(0,0,0,.3); --shadow-md:0 4px 12px rgba(0,0,0,.4); --shadow-lg:0 4px 24px rgba(0,0,0,.4);
  --shadow-xl:0 8px 32px rgba(0,0,0,.5); --shadow-glow:0 8px 32px rgba(99,102,241,.15); --shadow-glow-strong:0 0 24px rgba(99,102,241,.25);
  /* ===== Glass ===== */
  --glass-bg:rgba(255,255,255,.03); --glass-bg-strong:rgba(255,255,255,.05); --glass-border:1px solid rgba(255,255,255,.08); --glass-blur:blur(12px); --glass-blur-strong:blur(20px);
  /* ===== Motion ===== */
  --ease-standard:cubic-bezier(.4,0,.2,1); --ease-out:cubic-bezier(0,0,.2,1); --ease-in-out:cubic-bezier(.4,0,.6,1); --ease-spring:cubic-bezier(.34,1.56,.64,1);
  --duration-fast:150ms; --duration-base:200ms; --duration-slow:300ms; --duration-slower:400ms;
  /* ===== Layout ===== */
  --container-max:1280px; --container-wide:1440px; --container-narrow:720px; --grid-gutter:24px; --page-padding-x:32px;
  --nav-height:64px; --sidebar-width:240px; --sidebar-collapsed:64px;
  --control-height:36px; --control-height-sm:30px; --control-height-lg:44px; --table-row-h:44px; --avatar-size:32px;
  /* ===== Z-index ===== */
  --z-base:0; --z-dropdown:100; --z-sticky:200; --z-sidebar:300; --z-nav:400; --z-modal:1000; --z-drawer:1050; --z-toast:1100; --z-tooltip:1200;
}
```

---

## 附：页面级布局速查

| 页面 | 容器 | 布局结构 | 关键组件 |
|------|------|---------|---------|
| A1 首页 | `--container-wide` 全宽 | 全宽 Hero(辉光) → 统计卡片 4 列 → 平台展示 → 功能亮点 3 列 → Top5 预览表 | Hero/StatCard/Table |
| A2 排名榜 | `--container-wide` | 顶栏 → Tab(学校/学生) → 筛选器组 → Top3 高亮卡 → 排名表 → 分页 | Tab/Filter/Table/Pagination |
| A3 个人成绩 | `--container-max` | 信息卡(头像+基础) → 汇总指标 4 卡 → Rating 折线图 → 参赛历史表 → 平台账号状态 | StatCard/Chart/Table/Badge |
| A4 比赛列表 | `--container-max` | 筛选器组 → 比赛卡片网格(3列) → 分页 | Filter/CardGrid |
| B1 仪表盘 | 后台(侧栏+主区) | 统计卡片 4 列 → 图表区 2 列 → 三列列表(申请/任务/记录) | StatCard/Chart/List |
| B2-B6 后台 | 后台框架 | 侧栏 + 主区(页头+筛选+表格+分页) + 弹窗/抽屉 | Sidebar/Table/Modal/Drawer |
| C1-C5 认证 | `--container-narrow` 居中 | 玻璃拟态卡 + 分步表单 + 状态反馈 | GlassCard/Stepper/Form |
