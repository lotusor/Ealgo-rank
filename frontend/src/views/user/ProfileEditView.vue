<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updateMe, updateAvatar, listPlatformAccounts } from '@/api'
import type { PlatformAccount, UserMe } from '@/api/types'
import { useToast } from '@/composables/useToast'
import { initial } from '@/utils/format'
import PlatformAccountsEditor from '@/components/auth/PlatformAccountsEditor.vue'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const me = computed(() => auth.user)

// ---------- 头像 ----------
const avatarFile = ref<HTMLInputElement | null>(null)
const avatarBusy = ref(false)

function onPickAvatar() {
  avatarFile.value?.click()
}

async function onAvatarChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    toast.error('头像图片不能超过 2MB')
    input.value = ''
    return
  }
  avatarBusy.value = true
  try {
    const user = await updateAvatar(file)
    auth.setUser(user)
    toast.success('头像已更新')
  } catch (err: any) {
    toast.error(err?.message || '头像上传失败，请重试')
  } finally {
    avatarBusy.value = false
    input.value = ''
  }
}

async function onRemoveAvatar() {
  avatarBusy.value = true
  try {
    const user = await updateAvatar(null)
    auth.setUser(user)
    toast.success('头像已移除')
  } catch (err: any) {
    toast.error(err?.message || '操作失败，请重试')
  } finally {
    avatarBusy.value = false
  }
}

// ---------- 真实姓名 / 学号 ----------
const realName = ref('')
const studentNo = ref('')
const identityBusy = ref(false)

function syncIdentity() {
  realName.value = me.value?.real_name ?? ''
  studentNo.value = me.value?.student_no ?? ''
}
onMounted(syncIdentity)
watch(() => [me.value?.real_name, me.value?.student_no], syncIdentity)

async function saveIdentity() {
  identityBusy.value = true
  try {
    const user = await updateMe({
      real_name: realName.value.trim(),
      student_no: studentNo.value.trim(),
    })
    auth.setUser(user)
    toast.success('身份信息已保存')
  } catch (err: any) {
    toast.error(err?.message || '保存失败，请重试')
  } finally {
    identityBusy.value = false
  }
}

// ---------- 个性签名 ----------
const bio = ref('')
const bioBusy = ref(false)

function syncBio() {
  bio.value = me.value?.bio ?? ''
}
onMounted(syncBio)
// 用户数据可能异步到位，监听一次
watch(() => me.value?.bio, syncBio)

async function saveBio() {
  bioBusy.value = true
  try {
    const user = await updateMe({ bio: bio.value.trim() })
    auth.setUser(user)
    toast.success('个性签名已保存')
  } catch (err: any) {
    toast.error(err?.message || '保存失败，请重试')
  } finally {
    bioBusy.value = false
  }
}

// ---------- 平台账号 ----------
const accounts = ref<PlatformAccount[]>([])
const accountsLoading = ref(false)

async function loadAccounts() {
  accountsLoading.value = true
  try {
    accounts.value = await listPlatformAccounts()
  } catch {
    /* 忽略：未登录或网络异常 */
  } finally {
    accountsLoading.value = false
  }
}
onMounted(loadAccounts)

function onAccountsChanged() {
  loadAccounts()
  // 同步刷新 auth.user.platform_accounts，让个人中心展示即时更新
  auth.loadMe().catch(() => {})
}
</script>

<template>
  <div class="container-wide" style="max-width: 720px">
    <div class="page-head">
      <div>
        <div class="breadcrumb"><a @click="router.push('/u/my-scores')">个人中心</a><span>/</span><span>编辑资料</span></div>
        <h1 class="page-title">编辑资料</h1>
      </div>
    </div>

    <!-- 头像 + 用户名 -->
    <div class="card card-pad" style="margin-bottom: var(--space-6)">
      <div style="display: flex; align-items: center; gap: var(--space-5); flex-wrap: wrap">
        <div class="avatar-edit">
          <img v-if="me?.avatar" :src="me.avatar" class="avatar-img" alt="头像" />
          <div v-else class="avatar-img avatar-fallback">{{ initial(me?.real_name || me?.username || '?') }}</div>
          <div class="avatar-actions">
            <button class="btn btn-secondary btn-sm" :disabled="avatarBusy" @click="onPickAvatar">
              {{ avatarBusy ? '上传中…' : '更换头像' }}
            </button>
            <button v-if="me?.avatar" class="btn btn-ghost btn-sm text-danger" :disabled="avatarBusy" @click="onRemoveAvatar">
              移除
            </button>
          </div>
          <input ref="avatarFile" type="file" accept="image/*" style="display: none" @change="onAvatarChange" />
        </div>
        <div style="flex: 1; min-width: 200px">
          <div class="field">
            <label class="field-label">用户名</label>
            <input class="input" :value="me?.username" readonly placeholder="用户名" />
            <div class="field-hint">用户名用于排行榜与身份识别，已设置后不可修改</div>
          </div>
          <div class="field-grid">
            <div class="field">
              <label class="field-label">真实姓名</label>
              <input v-model="realName" class="input" maxlength="50" placeholder="选填，便于核验身份" />
            </div>
            <div class="field">
              <label class="field-label">学号</label>
              <input v-model="studentNo" class="input" maxlength="50" placeholder="选填" />
            </div>
          </div>
          <div class="field-hint" style="margin-bottom: var(--space-4)">
            真实姓名会展示在你的公开主页；学号仅本人与管理员可见
          </div>
          <button class="btn btn-primary btn-sm" :disabled="identityBusy" @click="saveIdentity">
            {{ identityBusy ? '保存中…' : '保存身份信息' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 个性签名 -->
    <div class="card card-pad" style="margin-bottom: var(--space-6)">
      <div class="field">
        <label class="field-label">个性签名</label>
        <textarea
          v-model="bio"
          class="input"
          rows="2"
          maxlength="200"
          placeholder="一句话介绍自己（最多 200 字）"
        />
        <div class="field-hint" style="display: flex; justify-content: space-between">
          <span>{{ bio.length }}/200</span>
        </div>
      </div>
      <button class="btn btn-primary btn-sm" :disabled="bioBusy" @click="saveBio">
        {{ bioBusy ? '保存中…' : '保存签名' }}
      </button>
    </div>

    <!-- 平台账号绑定 -->
    <div class="card card-pad">
      <div class="section-title" style="margin-bottom: var(--space-2)">竞赛平台账号</div>
      <p class="body-sm text-secondary" style="margin-bottom: var(--space-5)">
        绑定你在 Codeforces / AtCoder / 牛客 的账号 ID，用于同步参赛成绩并纳入学校排名。平台账号 ID 一周仅可修改一次。
      </p>
      <div v-if="accountsLoading" class="caption text-tertiary">加载中…</div>
      <PlatformAccountsEditor v-else :accounts="accounts" @changed="onAccountsChanged" />
    </div>
  </div>
</template>

<style scoped>
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
@media (max-width: 560px) { .field-grid { grid-template-columns: 1fr; } }
.avatar-edit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}
.avatar-img {
  width: 96px;
  height: 96px;
  border-radius: var(--radius-xl);
  object-fit: cover;
  box-shadow: var(--shadow-glow);
}
.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  background: var(--gradient-primary);
}
.avatar-actions {
  display: flex;
  gap: var(--space-2);
}
.text-danger {
  color: var(--color-danger);
}
</style>
