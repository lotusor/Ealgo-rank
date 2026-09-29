<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  listUsers, listSchools, setUserRole,
  listAdminPlatformAccounts, adminUnbindPlatformAccount,
  adminRebindPlatformAccount, adminBindPlatformAccount, listHandleAudits,
} from '@/api'
import type {
  UserRoster, School, AdminPlatformAccount, HandleAuditRow,
} from '@/api/types'
import { useToast } from '@/composables/useToast'
import DataPagination from '@/components/ui/DataPagination.vue'
import { fmtDate } from '@/utils/format'
import { BINDABLE_COUNT, BINDABLE_PLATFORMS } from '@/platforms/meta'

const auth = useAuthStore()
const toast = useToast()

const data = ref<UserRoster[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const settling = ref<number | null>(null)

const roleOptions = [
  { value: 'user', label: '普通用户' },
  { value: 'school_admin', label: '学校管理员' },
] as const

const keyword = ref('')
const bind = ref<'all' | 'full' | 'partial'>('all')
const schools = ref<School[]>([])
const schoolSel = ref<number | null>(null)

// 「全绑了」的分母是可绑定平台数，不是硬编码 3：只做赛程展示的平台（洛谷）
// 不提供绑定入口，把它算进分母会让所有人都永远「未完全绑定」
const BIND_TOTAL = BINDABLE_COUNT
const bindOptions = [
  { label: '全部绑定状态', value: 'all' as const },
  { label: `${BIND_TOTAL} 平台已绑定`, value: 'full' as const },
  { label: '部分绑定', value: 'partial' as const },
]

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (auth.isSuperAdmin && schoolSel.value) params.school = schoolSel.value
    const res = await listUsers(params)
    let rows = res.results
    if (bind.value === 'full') rows = rows.filter((u) => u.platform_accounts_count >= BIND_TOTAL)
    else if (bind.value === 'partial') rows = rows.filter((u) => u.platform_accounts_count < BIND_TOTAL)
    data.value = rows
    total.value = res.count
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onRoleChange(u: UserRoster, ev: Event) {
  const el = ev.target as HTMLSelectElement
  const next = el.value
  const label = roleOptions.find((o) => o.value === next)?.label ?? next
  if (
    !confirm(
      `确认将「${u.real_name || u.username}」的角色调整为「${label}」？`,
    )
  ) {
    el.value = u.role
    return
  }
  settling.value = u.id
  try {
    const updated = await setUserRole(u.id, next as 'user' | 'school_admin')
    u.role = updated.role
    u.role_display = updated.role_display
    toast.success(`已将「${updated.real_name || updated.username}」调整为「${updated.role_display}」`)
  } catch (e: any) {
    el.value = u.role
    toast.error(e?.response?.data?.detail || '调整失败')
  } finally {
    settling.value = null
  }
}

async function loadSchools() {
  if (!auth.isSuperAdmin) return
  try {
    const res = await listSchools({ page_size: 200 })
    schools.value = res.results
  } catch {
    /* 忽略 */
  }
}

function roleCls(r: string) {
  return r === 'super_admin' ? 'badge-danger' : r === 'school_admin' ? 'badge-warning' : 'badge-muted'
}

function resetPage() {
  page.value = 1
  load()
}

// ---------- 平台账号归属管理（随时解绑 / 换绑 / 代绑） ----------
// 平台 ID 没有归属证明手段，自助绑定是「先到先得」：填错、被别人抢先绑定都要
// 管理员能立刻纠正，所以这里的动作绕过一周与解绑冷却，但每步都写留痕。
const acctUser = ref<UserRoster | null>(null)
const accounts = ref<AdminPlatformAccount[]>([])
const audits = ref<HandleAuditRow[]>([])
const acctLoading = ref(false)
const busy = ref<number | 'bind' | null>(null)
const reason = ref('')
const rebindTo = ref<Record<number, string>>({})
const newBind = ref({ platform: BINDABLE_PLATFORMS[0]?.key ?? 'codeforces', handle: '' })

/** 后端错误既可能是 detail，也可能是 DRF 的 errors 字典，都要能显示出来。 */
function apiErr(e: any, fallback: string): string {
  const d = e?.response?.data
  if (d?.detail) return String(d.detail)
  const er = d?.errors
  if (er && typeof er === 'object') {
    for (const v of Object.values(er)) {
      if (Array.isArray(v) && v.length) return String(v[0])
      if (typeof v === 'string' && v) return v
    }
  }
  return fallback
}

async function refreshAccounts(u: UserRoster) {
  acctLoading.value = true
  try {
    const [acc, aud] = await Promise.all([
      listAdminPlatformAccounts({ user: u.id, page_size: 20 }),
      listHandleAudits({ user: u.id, page_size: 8 }),
    ])
    accounts.value = acc.results
    audits.value = aud.results
  } catch (e: any) {
    toast.error(apiErr(e, '加载平台账号失败'))
  } finally {
    acctLoading.value = false
  }
}

async function openAccounts(u: UserRoster) {
  acctUser.value = u
  reason.value = ''
  rebindTo.value = {}
  newBind.value = { platform: BINDABLE_PLATFORMS[0]?.key ?? 'codeforces', handle: '' }
  await refreshAccounts(u)
}

async function afterMutation() {
  if (acctUser.value) await refreshAccounts(acctUser.value)
  await load()
}

async function doUnbind(a: AdminPlatformAccount) {
  const ok = confirm(
    `确认解绑「${a.username}」的 ${a.platform_display} 账号 ID ${a.handle}？\n\n` +
    `该账号名下 ${a.participation_count} 条参赛记录会一并删除并触发排名重算（不可恢复）。`)
  if (!ok) return
  busy.value = a.id
  try {
    const res = await adminUnbindPlatformAccount(a.id, reason.value.trim())
    toast.success(res.detail || '已解绑')
    await afterMutation()
  } catch (e: any) {
    toast.error(apiErr(e, '解绑失败'))
  } finally {
    busy.value = null
  }
}

async function doRebind(a: AdminPlatformAccount) {
  const next = (rebindTo.value[a.id] || '').trim()
  if (!next) {
    toast.error('请先填写新的平台账号 ID')
    return
  }
  const ok = confirm(
    `确认把「${a.username}」的 ${a.platform_display} 账号 ID 由 ${a.handle} 改为 ${next}？\n\n` +
    `改名语义：已入库的旧 ID 成绩仍留在该账号名下；新 ID 的历史成绩随后自动补抓。`)
  if (!ok) return
  busy.value = a.id
  try {
    await adminRebindPlatformAccount(a.id, next, reason.value.trim())
    toast.success('已改绑，历史成绩补抓已排队')
    await afterMutation()
  } catch (e: any) {
    toast.error(apiErr(e, '改绑失败'))
  } finally {
    busy.value = null
  }
}

async function doBind() {
  const handle = newBind.value.handle.trim()
  if (!handle || !acctUser.value) {
    toast.error('请填写要绑定的平台账号 ID')
    return
  }
  busy.value = 'bind'
  try {
    await adminBindPlatformAccount(
      acctUser.value.id, newBind.value.platform, handle, reason.value.trim())
    toast.success(`已为「${acctUser.value.real_name || acctUser.value.username}」绑定 ${handle}`)
    newBind.value.handle = ''
    await afterMutation()
  } catch (e: any) {
    toast.error(apiErr(e, '绑定失败'))
  } finally {
    busy.value = null
  }
}

function auditCls(action: string) {
  if (action.startsWith('admin_')) return 'badge-warning'
  if (action.endsWith('unbind') || action.endsWith('rebind')) return 'badge-danger'
  return 'badge-muted'
}

onMounted(() => {
  load()
  loadSchools()
})
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><span>管理后台</span><span>/</span><span>成员名单</span></div>
        <h1 class="page-title">成员名单</h1>
        <p class="page-subtitle">本校已注册并绑定平台账号的学生列表</p>
      </div>
    </div>

    <div class="filter-bar">
      <div class="input-group" style="flex: 1; max-width: 320px">
        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
        <input v-model="keyword" class="input" type="text" placeholder="搜索姓名 / 学号 / 用户名…" @keyup.enter="resetPage" />
      </div>
      <select v-if="auth.isSuperAdmin" v-model.number="schoolSel" class="input" style="width: auto" @change="resetPage">
        <option :value="null">全部学校</option>
        <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select v-model="bind" class="input" style="width: auto" @change="resetPage">
        <option v-for="o in bindOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <button class="btn btn-ghost" @click="resetPage">查询</button>
      <span class="caption text-tertiary" style="margin-left: auto">共 <b class="num">{{ total }}</b> 人</span>
    </div>

    <div class="card" style="overflow: hidden">
      <div class="table-wrap" style="border: none; border-radius: 0">
        <table class="data-table">
          <colgroup>
            <col style="width: 15%" />
            <col style="width: 13%" />
            <col style="width: 12%" />
            <col style="width: 16%" />
            <col style="width: 9%" />
            <col style="width: 12%" />
            <col style="width: 11%" />
            <col style="width: 12%" />
          </colgroup>
          <thead>
            <tr><th>用户名</th><th>真实姓名</th><th>学号</th><th>学校</th><th class="num-cell">平台账号</th><th>角色</th><th class="num-cell">注册时间</th><th class="num-cell">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="u in data" :key="u.id">
              <td class="cell-strong">{{ u.username }}</td>
              <td>{{ u.real_name || '—' }}</td>
              <td class="num-cell">{{ u.student_no || '—' }}</td>
              <td class="cell-ellipsis">{{ u.school_name || '—' }}</td>
              <td class="num-cell num">
                <span :class="u.platform_accounts_count >= BIND_TOTAL ? 'text-success' : 'text-warning'">{{ u.platform_accounts_count }}</span>
                <span class="text-tertiary">/{{ BIND_TOTAL }}</span>
              </td>
              <td>
                <select
                  v-if="auth.isSuperAdmin && u.role !== 'super_admin'"
                  class="input"
                  style="width: auto; padding: 4px 8px; font-size: 13px"
                  :value="u.role"
                  :disabled="settling === u.id"
                  @change="onRoleChange(u, $event)"
                >
                  <option v-for="o in roleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
                <span v-else class="badge" :class="roleCls(u.role)">{{ u.role_display }}</span>
              </td>
              <td class="num-cell">{{ fmtDate(u.date_joined) }}</td>
              <td class="num-cell">
                <button class="btn btn-ghost btn-sm" @click="openAccounts(u)">平台账号</button>
              </td>
            </tr>
            <tr v-if="!data.length"><td colspan="8" class="empty-cell">暂无成员</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <DataPagination v-model:page="page" :page-size="pageSize" :total="total" @update:page="(p) => { page = p; load() }" />

    <!-- 平台账号归属管理 -->
    <div v-if="acctUser" class="modal-overlay" @click.self="acctUser = null">
      <div class="modal" style="width: 720px; max-width: 96vw">
        <div class="modal-header">
          平台账号 · {{ acctUser.real_name || acctUser.username }}
        </div>
        <div class="modal-body" :aria-busy="acctLoading">
          <p class="field-hint">
            解绑会删除该 ID 名下的全部参赛记录；改绑是「改名」语义，已入库的旧 ID 成绩仍留在该账号名下。
            要把成绩整体挪到另一个人，请先解绑错的一方，再为正确的人绑定。
          </p>

          <table class="data-table">
            <thead>
              <tr><th>平台</th><th>账号 ID</th><th class="num-cell">成绩</th><th>状态</th><th class="num-cell">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="a in accounts" :key="a.id">
                <td><span class="badge badge-muted">{{ a.platform_display }}</span></td>
                <td class="cell-strong">
                  {{ a.handle }}
                  <div v-if="a.released_at" class="field-hint">该 ID 曾在 {{ fmtDate(a.released_at) }} 被卸下</div>
                </td>
                <td class="num-cell num">{{ a.participation_count }}</td>
                <td>
                  <span v-if="a.verified" class="badge badge-success">已核实</span>
                  <span v-else class="badge badge-warning">待核实</span>
                </td>
                <td class="num-cell">
                  <div class="acct-actions">
                    <input
                      v-model="rebindTo[a.id]"
                      class="input rebind-input"
                      type="text"
                      :placeholder="`新 ${a.platform_display} ID`"
                      :aria-label="`改绑 ${a.username} 的 ${a.platform_display} 账号 ID`"
                    />
                    <button
                      class="btn btn-ghost btn-sm"
                      :disabled="busy === a.id || !(rebindTo[a.id] || '').trim()"
                      @click="doRebind(a)"
                    >改绑</button>
                    <button
                      class="btn btn-danger btn-sm"
                      :disabled="busy === a.id"
                      @click="doUnbind(a)"
                    >解绑</button>
                  </div>
                </td>
              </tr>
              <tr v-if="!accounts.length && !acctLoading">
                <td colspan="5" class="empty-cell">该用户还没有绑定任何平台账号</td>
              </tr>
            </tbody>
          </table>

          <div class="bind-row">
            <select v-model="newBind.platform" class="input" style="width: auto" aria-label="选择平台">
              <option v-for="p in BINDABLE_PLATFORMS" :key="p.key" :value="p.key">{{ p.label }}</option>
            </select>
            <input
              v-model="newBind.handle"
              class="input"
              type="text"
              style="flex: 1"
              placeholder="平台账号 ID（CF=handle，AtCoder=用户名，牛客=uid）"
              aria-label="要绑定的平台账号 ID"
              @keyup.enter="doBind"
            />
            <button class="btn btn-primary btn-sm" :disabled="busy === 'bind' || !newBind.handle.trim()" @click="doBind">
              {{ busy === 'bind' ? '绑定中…' : '代为绑定' }}
            </button>
          </div>

          <div class="field" style="margin-top: var(--space-4)">
            <label class="field-label" for="acct-reason">操作理由（写入留痕，可空）</label>
            <input id="acct-reason" v-model="reason" class="input" type="text" maxlength="200" placeholder="如：本人申诉，ID 填错" />
          </div>

          <div class="audit-box">
            <div class="caption text-tertiary">最近归属变动</div>
            <ul v-if="audits.length" class="audit-list">
              <li v-for="h in audits" :key="h.id">
                <span class="badge" :class="auditCls(h.action)">{{ h.action_display }}</span>
                <b class="num">{{ h.handle }}</b>
                <span class="text-tertiary">{{ fmtDate(h.created_at) }}</span>
                <span v-if="h.actor_name">· 操作人 {{ h.actor_name }}</span>
                <span v-if="h.reason" class="text-tertiary">· {{ h.reason }}</span>
              </li>
            </ul>
            <p v-else class="caption text-tertiary">暂无留痕</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="acctUser = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-5); }
.filter-bar { flex-wrap: wrap; }
.acct-actions { display: flex; gap: var(--space-2); justify-content: flex-end; align-items: center; }
.acct-actions .rebind-input { width: 150px; }
.bind-row { display: flex; gap: var(--space-2); align-items: center; margin-top: var(--space-4); }
.audit-box { margin-top: var(--space-4); border-top: 1px solid var(--color-border); padding-top: var(--space-3); }
.audit-list { list-style: none; margin: var(--space-2) 0 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.audit-list li { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; font-size: 13px; }
@media (max-width: 768px) {
  /* 窄屏下改绑输入换行，避免把操作列挤成不可点 */
  .acct-actions { flex-wrap: wrap; }
  .acct-actions .rebind-input { width: 100%; }
  .bind-row { flex-wrap: wrap; }
}
</style>
