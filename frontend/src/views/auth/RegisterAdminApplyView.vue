<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { createApplication, listSchools } from '@/api'
import type { School } from '@/api/types'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const choice = ref<'skip' | 'apply'>('skip')
const schools = ref<School[]>([])
const schoolId = ref<number | null>(auth.user?.school?.id ?? null)
const reason = ref('')
const contact = ref('')
const evidenceFile = ref<File | null>(null)
const loading = ref(false)
const showDone = ref(false)

const schoolOptions = computed(() => schools.value.map((s) => ({ label: s.name, value: s.id })))

onMounted(async () => {
  try {
    const res = await listSchools({ page_size: 200 })
    schools.value = res.results
  } catch {
    toast.error('学校列表加载失败')
  }
})

function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  evidenceFile.value = f ?? null
}

async function submitApply() {
  if (!schoolId.value) {
    toast.error('请选择要申请的学校')
    return
  }
  if (!reason.value.trim()) {
    toast.error('请填写申请理由')
    return
  }
  if (!contact.value.trim()) {
    toast.error('请填写联系方式')
    return
  }
  loading.value = true
  try {
    await createApplication({
      school: schoolId.value,
      reason: reason.value.trim(),
      contact: contact.value.trim(),
      evidence: evidenceFile.value ?? undefined,
    })
    showDone.value = true
  } catch (e: any) {
    const d = e?.response?.data
    let msg = '提交失败，请稍后重试'
    if (d?.school) msg = `学校：${Array.isArray(d.school) ? d.school.join('；') : d.school}`
    else if (d?.detail) msg = d.detail
    else if (typeof d === 'string') msg = d
    toast.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div style="position: absolute; inset: 0; background: var(--gradient-hero-glow); pointer-events: none" />
    <a class="auth-brand" @click="router.push({ name: 'home' })">
      <span class="brand-mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><path d="M3 17l4-4 4 4 4-8 4 8" /></svg></span>
      <span>E-algo <span class="brand-accent">Rank</span></span>
    </a>

    <div class="auth-card" style="max-width: 520px">
      <h2 class="h3" style="margin-bottom: var(--space-2)">申请成为学校管理员</h2>
      <p class="body-sm text-secondary" style="margin-bottom: var(--space-6)">管理员可管理本校学生名单、审核参赛记录，申请需等待超级管理员审批</p>

      <div v-if="!showDone">
        <div class="segmented" style="margin-bottom: var(--space-6); background: var(--color-bg-inset)">
          <button class="seg-btn" :class="{ active: choice === 'skip' }" @click="choice = 'skip'">暂不申请</button>
          <button class="seg-btn" :class="{ active: choice === 'apply' }" @click="choice = 'apply'">我要申请</button>
        </div>

        <div v-if="choice === 'apply'">
          <div class="alert alert-warning" style="margin-bottom: var(--space-4)">
            申请将由超级管理员审核，结果在「系统公告」中发布；审核期间你仍可使用普通用户功能。
          </div>
          <div class="field">
            <label class="field-label">选择学校</label>
            <select v-model="schoolId" class="select">
              <option :value="null" disabled>申请管理的学校</option>
              <option v-for="s in schoolOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="field">
            <label class="field-label">申请理由</label>
            <textarea v-model="reason" class="textarea" rows="3" placeholder="请简述你申请管理员的原因，如：我是校 ACM 集训队队长…" />
          </div>
          <div class="field">
            <label class="field-label">联系方式</label>
            <input v-model="contact" class="input" placeholder="微信 / 邮箱 / QQ" />
          </div>
          <div class="field">
            <label class="field-label">上传证明材料（选填）</label>
            <label class="upload-drop">
              <input type="file" accept="image/*,.pdf" style="display: none" @change="onFile" />
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-tertiary)" stroke-width="1.5" style="margin: 0 auto var(--space-2)"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M17 8l-5-5-5 5M12 3v12" /></svg>
              <div class="body-sm text-secondary">{{ evidenceFile ? evidenceFile.name : '点击或拖拽上传文件' }}</div>
              <div class="caption text-tertiary" style="margin-top: 4px">支持学生证、社团证明 · JPG/PDF</div>
            </label>
          </div>
          <button class="btn btn-primary btn-block btn-lg" :disabled="loading" @click="submitApply">
            {{ loading ? '提交中…' : '提交申请' }}
          </button>
        </div>

        <div v-else style="text-align: center; padding: var(--space-4) 0">
          <p class="body-sm text-secondary" style="margin-bottom: var(--space-5)">你可以稍后再申请成为学校管理员。先去探索排名榜吧。</p>
          <button class="btn btn-primary btn-block btn-lg" @click="router.push({ name: 'rankings' })">进入榜单</button>
        </div>
      </div>

      <div v-else style="text-align: center; padding: var(--space-4) 0">
        <div style="width: 64px; height: 64px; border-radius: var(--radius-full); background: var(--color-warning-subtle, rgba(245,158,11,.12)); display: flex; align-items: center; justify-content: center; margin: 0 auto var(--space-5)">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning, #f59e0b)" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>
        </div>
        <h3 class="h3" style="margin-bottom: var(--space-2)">申请已提交</h3>
        <p class="body-sm text-secondary" style="margin-bottom: var(--space-6)">你的管理员申请已提交，请等待超级管理员审批。<br>审批结果将通过站内消息通知你。</p>
        <button class="btn btn-primary btn-block btn-lg" @click="router.push({ name: 'rankings' })">返回首页</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-drop {
  display: block;
  border: 1.5px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
  transition: all var(--duration-base);
}
.upload-drop:hover { border-color: var(--color-primary); background: var(--color-bg-overlay); }
</style>
